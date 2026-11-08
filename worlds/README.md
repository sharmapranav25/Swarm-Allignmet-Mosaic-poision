# World construction plans

These worlds share a testable question: can a small, blind intervention in distributed information change an agent's consequential action in a traceable way? Traceable use and a policy violation are separate claims.

| World | Current status | Consequential action | Additional requirement |
|---|---|---|---|
| [Ticketing](ticketing.md) | Runnable; linked page preserves historical results | Retrieve broad diagnostics, then close tickets | Current Gap 1 results are pending; see run artifacts |
| [Website maintenance](website-breach.md) | Build specification | Cross a simulated access boundary and use returned evidence | Closest reuse of ticketing |
| [Warehouse/shipping](warehouse-shipping.md) | Build specification | Dispatch to an unapproved destination and claim fulfilment | Shipment/approval provenance and inventory reservations |
| [Performance reporting](performance-reporting.md) | Build specification | Earn repeated display credit from the same completed work | Separate vulnerable counter from verified work; legitimate retry controls |
| [Stock market](stock-market.md) | Build specification; attribution extension unresolved | Trade after combining confidential fragments | Derived predictions and randomized ticker-choice controls; ticker match alone is insufficient |

Read [BUILD_CONTRACT.md](BUILD_CONTRACT.md) before implementing any world. Initial builds use three workers, two days, deterministic data tools, a blind Supervisor and blind Charlatan. The Charlatan selects its own field and value; documents must not prescribe that choice in defender prompts.

Reuse the existing streamed agent loop, retries, schema validation and ledger. Extract the intervention registry and world adapter next; the existing ticketing checkpoint runner is not yet generic. Implement website first, then warehouse and reporting; construct the stock engine independently while resolving its different attribution requirements.

These files authorize no claims of cross-world success. Only ticketing is runnable here, and historical ticketing success does not establish that the current randomized experiment or these proposed worlds pass. No new world implementation or live run was created by this documentation update.
