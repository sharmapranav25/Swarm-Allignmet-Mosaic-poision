# Historical example results

Three original `summary.json` files are copied unchanged, named by their original run IDs. Their values were recomputed against the source ledgers before export and matched exactly.

Each `.evidence.json` contains selected original ledger events (configuration, enrollments, intake, flags, plants, requests, receipts, action reviews, errors and completion) and the SHA-256 of its full source ledger. Per-ticket resolutions and the full model trace are omitted to keep the export compact. The selected events alone cannot independently reproduce every summary count.

The original complete ledgers remain under the source project's `runs/<original-run-id>/ledger.jsonl`; they are not required to run this standalone project. Fresh runs create their own complete ledgers locally. This export contains no API key.

- [Latest run review](LATEST_RUN_REVIEW.md)
- [Intake, seed 2](ticketing_brief10_s2.summary.json)
- [No-intake baseline, seed 1](ticketing_blind10_s1.summary.json)
- [No-intake baseline, seed 2](ticketing_blind10_s2.summary.json)

Historical run configurations carried stale stock-world population fields. The `enroll` events and summaries establish the actual 3 naive / 4 restrained / 3 rogue cast. Earlier no-intake runs omit a `briefs` flag but contain no intake events; the newer intake run explicitly records `briefs: true`.
