# Minimal original observation procedure

Status: procedure defined; execution is pending authorized official inputs and a qualified Windows reference host.

1. Copy, never move, the supplied executable, installation data/assets, configuration, and save fixtures into a private read-only source area. Record source provenance without exposing private paths publicly.
2. Compute SHA-256 for every required input before and after transfer. Identify executable version, language, patch state, PE image base/sections, data edition, configuration, locale, and host/VM identity. Reject or register mismatches; do not rename them as the baseline.
3. Create a fresh per-attempt writable user/config/save directory. Mount or expose qualified inputs read-only. Record the allowlisted environment, clock policy, display/input adapter, instrumentation, resource limits, and exact commands.
4. Start with one bounded startup/load observation. Require the declared screen or game-state endpoint, expected execution path, logs, artifacts, and terminal record; process exit alone is insufficient.
5. Repeat the same observation without instrumentation and compare state/outcome to test neutrality. Then run A/A replay before using the result as an expected value.
6. Store raw artifacts privately and publish only hashes, schemas, synthetic fixtures, and permitted derived metadata. Link every conclusion to its attempt manifest. Unsupported capture, unexplained reads/imports, missing state, or a divergent repeat yields `inconclusive`.

Original-process observations and emulated routine tests are different evidence classes. Bosman agreement never substitutes for the original-process cross-check required by the verification plan.
