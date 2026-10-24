# Delivery workflow

This project uses ordinary Git branches, reviewed changes and documented phase gates. The phase documents define purpose, dependencies, scope and acceptance evidence. No external planning framework is required.

Before implementing a phase, confirm its dependencies, select a small bounded deliverable and freeze its acceptance cases. Reference the upstream integration contract and coverage register. Maintain source/build/input identities with every experiment.

Keep code and documentation changes reviewable. A phase closes only when executable evidence demonstrates its gate and all mandatory carry-forwards are resolved or explicitly accepted. Record actual outcomes separately from planned targets. Never bless a changed reference result just to make CI pass.

Changes to Rust as the core language, original baseline, whole-game scope, fidelity definitions or save/profile compatibility need an explicit recorded architectural decision. Routine choices within a bounded research campaign follow that campaign's approved policy.

The planning handoff applies only the documentation bundle. Implementation, deployment and publication follow the user's task instructions; this document adds no unrelated permission process.
