# Delivery workflow

This project uses ordinary Git branches, reviewed changes and documented phase gates. The phase documents define purpose, dependencies, scope and acceptance evidence. No external planning framework is required.

Start from [the active PC plan](../roadmap/PC_FIRST.md), confirm the selected package dependencies, and freeze its acceptance cases. Numbered phases define eventual closure, not a requirement to finish all infrastructure before a scoped numeric port. Reference the upstream integration contract and coverage register. Maintain source/build/input identities with every experiment.

Keep code and documentation changes reviewable. A phase closes only when executable evidence demonstrates its gate and all mandatory carry-forwards are resolved or explicitly accepted. Record actual outcomes separately from planned targets. Never bless a changed reference result just to make CI pass.

Changes to Rust as the core language, original baseline, whole-game scope, fidelity definitions or save/profile compatibility need an explicit recorded architectural decision. Routine choices within a bounded research campaign follow that campaign's approved policy.

Before merging, refresh against the target branch, run affected checks, and obtain independent review of the exact proposed revision under AGENTS.md. Record evidence and merge disposition in programme progress and the pull request. Never bypass frozen verification or branch protections to simplify cleanup. Live Windows execution additionally follows its dedicated operator ceremony; passing ordinary CI does not authorize it.
