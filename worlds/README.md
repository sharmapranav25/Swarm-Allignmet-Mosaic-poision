# Simulation worlds

Ticketing, website, warehouse and reporting each implement three alternative shortcut recipes.
Each world document specifies the distributed records, tool sequence, legitimate boundary and
observable misuse. All four reuse the shared agent transport, validation and append-only ledger.

| World | Recipes |
|---|---|
| [Ticketing](ticketing.md) | Broad bundle; foreign-case replay; bulk finalizer |
| [Website](website-breach.md) | Restricted request; environment crossing; maintenance bypass |
| [Warehouse](warehouse-shipping.md) | Diversion; duplicate replacement; false delivery |
| [Reporting](performance-reporting.md) | Event replay; attribution theft; overlapping merge |
| [Stock market](stock-market.md) | Separate historical/proposed market design; unchanged here |

Run `<world>.undefended` for the no-security baseline; `<world>.run` enables the defended world.
The baseline's ten epochs and five worker calls per epoch are distinct from defended-run defaults.
No new model runs were launched for the multi-secret implementation. Existing results test older
single-secret builds and must not be presented as validation of the added recipes.

The [build contract](BUILD_CONTRACT.md) records the original design constraints. Its staged rollout
language predates the current implementation. The checkpoint/random-assignment runner remains
ticketing-specific; adding recipes does not make it a generic cross-world experiment.
