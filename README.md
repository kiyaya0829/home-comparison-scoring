# Home Comparison Scoring — Smooth v2

A standalone Python scoring module for integration into the SC2006 Home Comparison System. It has no third-party runtime dependencies, reads no credentials, makes no API calls, and does not modify its inputs. The prototype parameters still require team validation; scores are not probabilities of satisfaction.

## Equations and parameters

- Weekly travel burden B = one-way minutes × visits per week × trip-leg factor. This module receives the precomputed `weekly_minutes` value and does not apply frequency again.
- Travel T = 100 × τ / (τ + B), with a default τ of 300 minutes.
- Proximity D = 100 × δ / (δ + d), with a default δ of 500 metres.
- Venue count N = 100 × n / (ν + n), with a default ν of 3. Here, n is the number of unique venues within 1 km.
- Amenity A = αD + (1−α)N, with a default α of 0.5.
- Overall fit S = Σ(w × criterion score) / Σw, with High / Medium / Low weights of 3 / 2 / 1.

τ, δ, and ν are the input values at which their respective components score 50; they are not maximum permitted values. Smooth functions avoid assigning zero to every value beyond a cutoff, while the venue-count component has diminishing returns. All amenity categories currently share the same parameters; category-specific calibration is not implemented.

## Evidence and result rules

The overall score uses only criteria with valid evidence for every candidate. Missing evidence is unavailable, not zero. If the nearest distance is unknown, the entire amenity criterion is unavailable. A valid observation of zero nearby venues remains a zero count. Negative values, non-finite values, and non-integer venue counts are rejected.

Coverage = number of shared available criteria / number of selected criteria × 100%. It is displayed separately and does not multiply the overall score.

- **Complete:** all selected criteria are comparable.
- **Partial:** some, but not all, selected criteria are comparable.
- **Inconclusive:** no criteria are jointly available.

Only Complete results return `highest_fit_candidates`. These identify the highest fit under this proposal, not a validated recommendation. The existing `warning` and `decision` fields continue to identify the experimental status.

Overall scores are rounded to two decimal places before sorting. Equal displayed scores share competition ranks, such as 1, 1, 3, and retain input order within a tie. Criterion scores and contributions retain their calculation precision. Python's `round` uses ties-to-even rounding.

`contributions` contains each criterion's weighted contribution. Each entry in `pairwise` contains `contribution_differences` between two homes. These differences sum to the difference between their unrounded overall scores; they are not measures of statistical confidence. Outputs record `version` and `parameters`. Reproducibility requires preserving both, together with the inputs and evidence snapshot.

## Usage

```python
from scoring import score, ExperimentalPolicy

criteria = [{"id": "work", "label": "Work", "importance": "High"}]
rows = [{"postal_code": "Example A", "metrics": {
    "work": {"type": "travel", "available": True, "weekly_minutes": 300}
}}]
result = score(rows, criteria)  # overall = 50.0

# Experiment with a different calibration parameter:
result = score(rows, criteria, policy=ExperimentalPolicy(travel_half=400))
```

Run the tests:

```sh
python -m unittest discover -s tests -v
```

See [docs/MIGRATION.md](docs/MIGRATION.md) for integration instructions. This package does not include the original project's data, environment files, or credentials, and does not modify that project.
