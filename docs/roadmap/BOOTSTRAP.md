# First implementation checkpoints

The objective of the opening work is to prove a complete evidence-to-Rust loop with minimal infrastructure, then make it durable. These checkpoints do not start implementation during this review.

| Checkpoint | Concrete deliverable | Acceptance | Can proceed without |
|---|---|---|---|
| B0 Inventory | Pinned upstream sources, raw map import and scope register | Idempotent parse, provenance/count reconciliation; unresolved binary checks explicit | VPS, Jev, original input for map-only work |
| B1 Execute | One local Bosman job under a Rust CLI | Correct input/build hashes, expected endpoint, logs and replay manifest | Database queue, dashboard, continuous service |
| B2 Compare | Controlled original/Bosman observation and comparator | A/A replay; first deliberate divergence detected; no masked semantic difference | VPS, Jev, broad research automation |
| B3 Reconstruct | First Rust numeric/RNG slice followed by bounded stateful squad command | Original-backed local parity, native/WASM replay and supported-state save/reload | Finished mapping platform, Jev evaluation |
| B4 Sustain | Durable queue, bounded worker and 24h VPS pilot | Successful scenario endpoints, recovery and no lost accepted evidence | Jev, large dashboard |
| B5 Research | Instrumented evidence workflow and 72h campaign | Useful reviewed contracts, negative control, bounded storage and restored backup | Model services if reviewed evidence can be produced manually |

B0/B1 are the first active packages. Reference work B2 and service hardening B4 may overlap after their inputs exist. B3 begins when the relevant local calibration is adequate; its acceptance still requires the P02/P04 gate evidence. Optional Jev evaluation never blocks the first Rust feature.

Defer elaborate dashboards, distributed workers, large model pipelines and elaborate crate splitting until these checkpoints expose a need. Start with a Cargo workspace containing a small core/protocol and lab CLI; split crates at demonstrated boundaries. PostgreSQL remains the selected durable backend, introduced when unattended queue semantics are needed. No second production scheduler is created for the local spike.

If B1 cannot run, solve inputs/build/adapter before adding services. If B2 cannot replay, solve capture/numerics/layout before broad porting. If B3 cannot compose a valid stateful feature, use the dependency ledger to redesign that slice. These are actionable stop conditions for affected work, not blanket pauses on all inventory and documentation.
