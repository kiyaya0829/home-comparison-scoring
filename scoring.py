"""Replaceable scoring policy over collected evidence; never fetches providers."""
from typing import Protocol
from math import isfinite

VERSION = "smooth-v2-proposal"
WEIGHTS = {"High": 3, "Medium": 2, "Low": 1}


def clamp(value):
    return max(0.0, min(100.0, value))


class ScoringPolicy(Protocol):
    version: str
    warning: str
    decision: str

    def criterion_score(self, metric: dict) -> float | None: ...
    def weight(self, importance: str) -> float: ...


class ExperimentalPolicy:
    """Smooth scoring proposal. Parameters require team calibration."""
    version = VERSION
    warning = "Exploratory preview only. Formula, thresholds and Inconclusive rule await team agreement."
    decision = "No final highest-fit recommendation; scoring rules are not agreed."

    def weight(self, importance):
        return WEIGHTS[importance]

    def __init__(self, *, travel_half=300, distance_half=500, count_half=3, distance_weight=0.5):
        values = (travel_half, distance_half, count_half, distance_weight)
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) for v in values):
            raise ValueError("Scoring parameters must be finite numbers")
        if min(travel_half, distance_half, count_half) <= 0 or not 0 <= distance_weight <= 1:
            raise ValueError("Half-score parameters must be positive; distance_weight must be in [0, 1]")
        self.travel_half = travel_half
        self.distance_half = distance_half
        self.count_half = count_half
        self.distance_weight = distance_weight

    @property
    def parameters(self):
        return dict(travel_half=self.travel_half, distance_half=self.distance_half,
                    count_half=self.count_half, distance_weight=self.distance_weight)

    def criterion_score(self, metric):
        if not metric.get("available", False):
            return None
        def value(key):
            number = metric[key]
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not isfinite(number) or number < 0:
                raise ValueError(f"{key} must be a finite non-negative number")
            return number
        if metric["type"] == "travel":
            burden = value("weekly_minutes")
            return 100 * self.travel_half / (self.travel_half + burden)
        if metric["type"] != "amenity":
            raise ValueError("Unknown metric type")
        distance = value("nearest_metres")
        count = value("count_within_1km")
        if count != int(count):
            raise ValueError("Venue count must be an integer")
        proximity = 100 * self.distance_half / (self.distance_half + distance)
        quantity = 100 * count / (self.count_half + count)
        return self.distance_weight * proximity + (1 - self.distance_weight) * quantity


DEFAULT_POLICY: ScoringPolicy = ExperimentalPolicy()


def criterion_score(metric):
    return DEFAULT_POLICY.criterion_score(metric)


def _weighted_preview(rows, criteria, *, policy: ScoringPolicy | None = None):
    policy = policy or DEFAULT_POLICY
    if len({c["id"] for c in criteria}) != len(criteria):
        raise ValueError("Criterion IDs must be unique")
    for c in criteria:
        weight = policy.weight(c["importance"])
        if not isfinite(weight) or weight <= 0:
            raise ValueError("Weights must be positive finite numbers")
    shared = [c for c in criteria if rows and all(r["metrics"].get(c["id"], {}).get("available", False) for r in rows)]
    excluded = [c["id"] for c in criteria if c not in shared]
    scored = []
    for row in rows:
        scores = {c["id"]: policy.criterion_score(row["metrics"].get(c["id"], {"available": False})) for c in criteria}
        denominator = sum(policy.weight(c["importance"]) for c in shared)
        overall = sum(scores[c["id"]] * policy.weight(c["importance"]) for c in shared) / denominator if denominator else None
        scored.append({"postal_code": row["postal_code"], "scores": scores,
                       "overall": round(overall, 2) if overall is not None else None,
                       "contributions": {c["id"]: scores[c["id"]] * policy.weight(c["importance"]) / denominator for c in shared}})
        if "candidate_id" in row:
            scored[-1].update(candidate_id=row["candidate_id"], label=row["label"])
    for item in scored:
        explanations = []
        if shared:
            strongest = max(shared, key=lambda c: item["scores"][c["id"]] * policy.weight(c["importance"]))
            explanations.append(f"{strongest['label']} contributes most to this experimental weighted score.")
            disadvantages = [(other["scores"][c["id"]] - item["scores"][c["id"]], other, c)
                             for c in shared for other in scored if other is not item]
            if disadvantages:
                gap, other, criterion = max(disadvantages, key=lambda x: x[0])
                if gap > 0:
                    explanations.append(f"{other.get('label') or other['postal_code']} performs better on {criterion['label']} under these trial rules.")
        if excluded:
            explanations.append("Overall preview excludes criteria without evidence for every home.")
        item["explanations"] = explanations
    ordered = sorted(scored, key=lambda r: -(r["overall"] if r["overall"] is not None else -1))
    previous = object()
    rank = None
    for position, item in enumerate(ordered, 1):
        if item["overall"] is not None:
            if item["overall"] != previous:
                rank = position
            previous = item["overall"]
            item["rank"] = rank
        else:
            item["rank"] = None
    coverage = 100 * len(shared) / len(criteria) if criteria else 0.0
    status = "Inconclusive" if not shared else "Complete" if len(shared) == len(criteria) else "Partial"
    pairwise = []
    for i, left in enumerate(ordered):
        for right in ordered[i + 1:]:
            pairwise.append({"left": left.get("candidate_id", left["postal_code"]),
                             "right": right.get("candidate_id", right["postal_code"]),
                             "contribution_differences": {c["id"]: left["contributions"][c["id"]] - right["contributions"][c["id"]] for c in shared}})
    return {"version": policy.version, "parameters": getattr(policy, "parameters", {}),
            "coverage": coverage, "status": status, "pairwise": pairwise,
            "highest_fit_candidates": [r.get("candidate_id", r["postal_code"]) for r in ordered if r["rank"] == 1] if status == "Complete" else [], "warning": policy.warning,
            "shared_criteria": [c["id"] for c in shared], "excluded_criteria": excluded,
            "rows": ordered, "decision": policy.decision,
            "tie_policy": "Equal two-decimal scores share competition rank and retain selection order.",
            "formula_description": "Smooth half-score policy; see returned parameters. Importance weights: High/Medium/Low = 3/2/1. Only shared available criteria enter the weighted mean. Custom policies define their own arithmetic."}


class Scorer(Protocol):
    def score(self, rows: list[dict], criteria: list[dict]) -> dict: ...


class ExperimentalScorer:
    def score(self, rows, criteria):
        return _weighted_preview(rows, criteria)


DEFAULT_SCORER: Scorer = ExperimentalScorer()


def score(rows, criteria, *, scorer: Scorer | None = None, policy: ScoringPolicy | None = None):
    """Replace the entire scorer, or just its components; evidence remains unchanged."""
    if policy is not None:
        return _weighted_preview(rows, criteria, policy=policy)
    return (scorer or DEFAULT_SCORER).score(rows, criteria)
