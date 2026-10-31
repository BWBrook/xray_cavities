# Independent Q-032 regeneration evidence

`independent_regeneration.tar.gz` preserves the independent temporary rebuild
without exposing it to Git CSV newline conversion. All five generated manifest
entries were verified. `comparison.json` records byte and parsed-record
comparisons against the merged checkout at fa175dbb: the CSVs differ only by
line endings, the figures are byte-identical, and metadata records the new
review commit. See `docs/science/q032_independent_review_2026-10-31.md`.

The focused test result (19 passed, 1 expected failure) was reported by the
independent subagent; no separate test stdout file was retained.
