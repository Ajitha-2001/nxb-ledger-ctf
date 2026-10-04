# Reference Solutions (Facilitator / Testing Use Only)

These scripts are **for the group's own testing** (T01-T14 in the design
report's Testing and Acceptance Plan) - they must never be distributed to
participants or included in the CTFd challenge attachments.

- `solve_stage6.py` - reference implementation of `correlate.py`, used to
  verify Stage 6's dataset is solvable and reproducible (T09: rerun with
  shuffled input rows and confirm the same `evidence.json` is produced).

Stages 1-5 don't need a scripted solver to test - their answers are fixed,
short values you can check by hand against
`evidence-generation/output/secrets/answer_key.json`, or by POSTing that
file's contents straight to the evidence-checker endpoints
(see `scripts/smoke_test.py`, which does exactly this for all four
checker-based stages).
