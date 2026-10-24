# From observed code to a working Rust game

## Select slices by dependency closure

The goal is a coherent game, not a collection of independently translated functions. Start from an observable player command or narrowly scoped algorithm. Identify its original entry points, direct and indirect callees, globals, object fields, constructors/destructors, allocation/lifetime rules, I/O and RNG effects. Record unresolved indirect targets rather than pretending a static call graph is complete.

Build a graph of function calls, data reads/writes, object ownership and event dependencies. Condense cycles into strongly connected groups to choose implementable units. The group is a scheduling aid, not proof of an isolated subsystem. Dynamic traces add reachable edges; absence from a trace does not show an edge is impossible. Preserve original address provenance through decompiler changes and Rust refactoring.

Each slice has a boundary ledger: required input state, dependencies supplied by real code, dependencies represented by captured fixtures, and unsupported paths. A test that stubs a callee cannot certify that callee or end-to-end integration. Track coverage of both branches and boundary state combinations.

## Reference execution and capture

For original-function experiments, record ABI, stack layout/alignment, registers, flags/FPU control, memory regions, alias relationships, required globals and imported functions. Capture a valid pre-call state from an observed path where possible. Unicorn runs a declared routine with those dependencies; it does not supply an entire Windows environment by itself.

Restore all relevant state between trials. Include heap allocation/free-list state when it affects behaviour. Reads outside captured regions, unknown imports, stale pointers or insufficient snapshots produce unsupported/inconclusive outcomes. Preserve touched memory and return state; identical return values with different side effects are a failure.

Separate fixture capture from decoding. Verify a decoder with original behaviour, field-boundary evidence and round-trip tests where applicable. Two implementations using the same incorrect decoder are not independent confirmation. Golden output comes from a pinned reference observation, not a Rust implementation used to test itself.

## Rust implementation boundary

Implement a slice in readable domain Rust after its behavioural contract is supported. Use explicit byte decoding for external records, narrow numeric compatibility helpers, stable typed IDs and ordered mutation. Original memory addresses are provenance/compatibility data, never unchecked native Rust references.

No transmute of arbitrary original save/memory bytes into Rust structs. Validate lengths, endianness, enum domains, ownership and referential integrity. Model legacy quirks with explicit safe values/operations; do not recreate undefined behaviour in Rust. Isolate any necessary unsafe/FFI code with a documented safety contract and focused checks. See [the Rust Reference](https://doc.rust-lang.org/reference/behavior-considered-undefined.html).

Floating-point precision, casts, signed division/remainders, overflow and comparison behaviour require targeted cases. Matching integer widths alone does not establish numeric equivalence. If virtual-address or allocator emulation is needed, keep it behind a compatibility boundary and validate original-address-sensitive cases before integrating it into domain logic.

## Incremental integration strategy

Default: execute standalone Rust slices over validated captured fixtures, compare them with original/Bosman observations, then compose slices into the Rust world. Rust and Bosman are separate backends. There is no assumption that an arbitrary Rust function can be dropped into the running translated game without a bridge.

A future mixed-runtime bridge requires a separate decision covering state ownership, callbacks, ABI, aliasing, RNG/clock ownership, error handling and conversion cost. It must prove conversion round-trips and that exactly one implementation owns each state transition. Until then, the browser prototype can operate only the supported Rust fixture; the original or Bosman application remains a separate reference application.

For each integrated feature, add a player workflow and save/reload scenario. Move from local function parity to ordered feature events, then day/world transitions and careers. Never label a synthetic fixture as a supported original full-save import.

## First proof and stopping rule

Begin with RNG/numeric compatibility against original routines and a bounded squad workflow: show a validated squad fixture, assign an eligible player to a lineup slot, reject an invalid assignment, save/reload the supported state. Confirm the exact original semantics and dependency closure before choosing its implementation entry points. If this command has unexpectedly broad dependencies, select another small stateful player command and record the reason; a read-only screen does not satisfy the stateful slice gate.

The first slice must expose at least one real difficulty in capture, side effects, arithmetic or integration and demonstrate how the method handles it. A new unmeasured abstraction is not success. If repeatability or dependency capture fails, pause broad porting of that affected area, reduce the case and report the remaining obstacle. Other verified areas can continue.

## Change impact and evidence freshness

Evidence is immutable and keyed by source binary, backend build/patches, scenario, input state, capture schema and comparison policy. A code/schema/profile change marks dependent conclusions stale for that identity; it does not erase historical findings. Use the dependency graph to choose retests only where dependency coverage is reliable; otherwise conservatively rerun the broader affected corpus. Imported names and model outputs alone never decide which regression tests can be skipped.
