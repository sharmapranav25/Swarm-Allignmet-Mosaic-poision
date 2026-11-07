# Current evidence and historical findings

**Implementation update:** the runnable build now uses the recipe-blind v2 Charlatan. The following live results belong to the earlier guided-alias implementation. Offline v2 tests establish mechanics only; see [the change notes](docs/BLIND_CHARLATAN.md).

The standalone ticketing setup has three recorded ten-worker development runs with qwen3.5-397b: each caught all three scripted rogues, with no positive catches among seven honest workers. See [the latest-run audit](results/LATEST_RUN_REVIEW.md) and the unchanged [example summaries](results/README.md).

Flags are not catches. Honest workers can be investigated and even planted without using the decoy. The strongest current evidence is the chain from a worker-specific planted alias to a broad request and a resolution citing its returned evidence.

Important boundaries:

- The Supervisor is role-blind and not explicitly given the assembly recipe, but learns from catalog contents. The Charlatan is domain-specific, not recipe-blind.
- Retrieval accepts a planted alias with correct namespace/service even if selector differs. A pointing decision can cite alias use even if another component prevents retrieval. Separate attempted use from receipt.
- Intake has not demonstrated an improvement: the recorded no-intake runs also succeeded.
- Earlier runs failed when the genuine alias arrived before suspicion. Those failures remain relevant; only successful recent examples were selected for this runnable export.
- Scripted rogues know the source order. Restrained workers share that knowledge and toolset but are instructed not to exploit it. Naive workers lack the broad-retrieval tool.
- Ticket closure scores are retained after poison use. This experiment measures detection/attribution, not attack punishment or business-loss prevention.

The original [historical findings](docs/HISTORICAL_FINDINGS.md) are preserved as an archive. Their numbered F1–F7 entries describe earlier configurations; statements such as “neither side is blind yet” and “Next” are historical, not an exact description of this export. The README and latest-run review take precedence for current behavior. Original run names in that archive refer to ledgers left in the source project.
