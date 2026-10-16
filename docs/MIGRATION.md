# Integration into SC2006_Prototype

1. Create a feature branch and preserve the original scoring module for rollback.
2. Copy this repository's `scoring.py` to `backend/closeforwhom/scoring.py`.
3. Keep the existing imports in `scoring_preview.py`: `VERSION`, `WEIGHTS`, `clamp`, `criterion_score`, and `score` remain available. The `scorer` and `policy` injection interfaces of `score` are preserved.
4. To display the new result fields, connect the frontend to `status`, `coverage`, `rank`, `contributions`, `pairwise`, and `highest_fit_candidates`. This repository does not include those UI changes. Existing response fields remain available.
5. When migrating the tests, change `from scoring import ...` to `from closeforwhom.scoring import ...`. Update the original `test_default_policy_preserves_existing_arithmetic` to reflect the new formula: 60 and 180 weekly minutes now produce 83.33 and 62.50, rather than 90 and 70.
6. Check the remaining project tests, snapshots, formula documentation, and UI text for references to the old 600 / 2000 / 10 thresholds. Run the full backend suite and the frontend flows involving scoring before merging.

## Importance-only reranking

The caller should pass the existing valid evidence snapshot and updated criteria without calling providers. This module does not retrieve data. Its offline tests verify pure calculation and input preservation; they do not establish that end-to-end integration with the original project has been tested.

## Input contract

Inputs retain the original project's structure: each row contains `postal_code` and `metrics`. Optional `candidate_id` and `label` fields distinguish listings that share a postal code. Criterion IDs must be unique, and importance values must be High, Medium, or Low.

Upstream code remains responsible for validating candidate counts, units, evidence validity, and snapshot freshness.

## Calibration and remaining work

The scoring rules remain a proposal. The team should calibrate parameters using several worked examples with realistic structures and synthetic values, and assess ranking sensitivity.

Category-specific parameters, automated sensitivity analysis, and inference of recommendation confidence are not implemented.
