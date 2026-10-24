# Inputs and decisions still needed

The roadmap is complete as a design proposal; the following block specific execution gates, not the creation of this plan.

| Item | Proposed default | Owner and gate |
|---|---|---|
| VPS OS, CPU architecture, RAM, free disk and existing services | Linux x86-64; start one worker and measure | Lister supplies facts before P01 deployment |
| Original executable/data/assets and reference saves | Official 3.9.68, original 2001 data, verified hashes | Lister supplies private input locations before P00 baseline run |
| Original reference host | Separate Windows host/VM; Linux Bosman used for bulk work | Implementer qualifies environment with Lister before P02 |
| Acceptable fidelity/deviation profile | Preserve original observable behaviour; explicit approved quirk fixes | Lister/implementer resolve measured conflicts in P02 |
| Browser memory/performance target | Measure representative worlds in P04; no fixed FPS/game-days target invented | Implementer at P04 |
| Original-save coverage | Import supported original saves; export to original format deferred | Confirm variants during P00 inventory; certify P09 |
| Supported original play modes | Inventory and retain; explicitly resolve any proposed exclusion | P00 inventory, P08/P09 closure |
| Off-host backup destination and spend ceiling | Daily consistent backup, no unbounded storage growth | Lister before unattended durability certification |
| Jev access, model, token budget and permitted input classes | Optional, disabled until configured; shadow evaluation in P03 | Lister supplies configuration; implementer evaluates |
| Reasoning-model service | Optional separate service, bounded evidence packets | Configure only when needed for P03 |
| First new feature | Choose after a faithful vertical slice exposes useful interfaces | Lister by P10; design hooks earlier |
| Licence for copied/adapted upstream material | Retain provenance; do not assume MIT covers GPL-derived code | Resolve before copying/distributing affected code |

No private credentials belong in this document or chat. Use deployment secret configuration when implementation starts.
