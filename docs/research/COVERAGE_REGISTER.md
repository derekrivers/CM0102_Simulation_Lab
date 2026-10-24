# Whole-game scope and coverage register

This is the initial scope checklist, not a claim that every original feature has been enumerated. P00 expands each row into observed original screens, actions, routines, data formats and acceptance cases. Unknown availability is recorded for investigation; it is not silently excluded. All implementation statuses are currently planned.

For every expanded entry record: stable scope ID, original evidence, upstream map references, Bosman capability, scenario IDs, phase owner, fidelity class, Rust module, UI journey, save impact, result revision, gaps and any accepted deviation. Completion requires evidence for the confirmed baseline scope. A total function count cannot close this register.

| Scope | Inventory and acceptance target | Delivery owner |
|---|---|---|
| Setup | Original new-game options, nations/leagues, database sizes, languages and manager setup | P00/P08 |
| World data | People, clubs, nations, competitions, relationships, identifiers, text encodings and date/currency representation | P04/P07 |
| Squad and tactics | Squad selection, eligibility, positions, formations, instructions and substitutions | P05/P06 |
| People lifecycle | Attributes, condition, morale, injuries, development/decline, retirement/regeneration and staff careers | P05/P07 |
| Training | Schedules, assignments, workload and observed development/condition effects | P05 |
| Recruitment | Scouting assignments/reports, search/filter/sort, information visibility and player knowledge | P05/P08 |
| Contracts and transfers | Offers, negotiations, wages, clauses, renewals, loans, free agents, deadlines and ownership changes present in the baseline | P05 |
| Club operation | Finances, budgets, facilities, board expectations/interactions, management jobs and dismissal | P05/P07 |
| Human and AI managers | Active decisions, assistant delegation and holiday behaviour; equivalent AI world paths | P05/P07 |
| Detailed matches | Tactical/player decisions, events, officials, penalties/extra time, ratings/statistics, commentary and post-match writes | P06 |
| Quick matches | Result path, path-selection policy and consistent competition/player writeback | P06/P07 |
| Competition rules | Each actual league/cup format, entrants, draws, tie-breakers, qualification, promotion/relegation and prize money | P07/P09 |
| Calendar | Fixture generation, postponements/rescheduling, competing schedules, windows, season turnover and special dates | P07 |
| International football | Squads/call-ups, eligibility, qualifiers, tournaments and club interactions actually present | P07 |
| Records and history | Tables/results, individual/club records, awards and historical accumulation | P07/P08 |
| News and interaction | Inbox, generated messages, available responses, deadlines and consequences | P05/P08 |
| UI and navigation | Every confirmed screen/action, links, sorting, keyboard behaviour, display settings and familiar presentation | P04–P08 |
| Assets and localisation | Images, fonts, palettes, text resources, any audio, language/encoding support and provenance | P00/P08 |
| Persistence | Original database/save import variants, new saves, autosave/backups, migration, interrupted writes and large saves | P04–P09 |
| Play modes | Inventory original multi-manager/hot-seat/network support, then document authority/reconnect behaviour for modes present | P00/P08/P09 |
| Browser operation | Worker lifecycle, large-world memory, yielding, progress/cancel, refresh/crash recovery and storage quota/export failures | P04/P08/P09 |
| Modifying the game | Versioned data/rules, editor/import validation, feature profiles, migrations and removal of extensions | P04/P10 |
| Research operations | Replay, tracing, comparison, reference calibration, upstream upgrades, recovery, storage retention and model budgets | P00–P03; continuous |

## Audit findings addressed in this revision

1. Upstream links existed in the source appendix, but the front-page roadmap did not show their operational importance. Both now appear in the main README, roadmap, stack and simulator documents, with a dedicated integration contract.
2. Map ingestion was sequenced too late. P00 imports the existing inventory; P03 enriches it. New mapping work must consult imported evidence first.
3. Upstream fixture availability, schema drift and qualification of upgrades needed explicit work. They now have procedures and phase gates.
4. The whole-game scope was spread across narrative. This register makes coverage omissions reviewable and requires feature-level expansion before scope closure.
5. Browser persistence/recovery and the data-editing workflow needed clearer treatment. They now have explicit workstream entries and phase additions.

## Remaining uncertainty

Full original feature enumeration requires direct game observation and binary/data inspection. Exact replay may be limited by original layout/numeric behaviour. Browser memory, VPS throughput, Jev usefulness and original-save compatibility require experiments. These are tracked work, not reasons to declare the roadmap exhaustive today.

P00 also audits any existing work from the earlier Reversal effort supplied or made accessible: executable hashes, scripts, screen maps, extracted asset manifests, saves and function findings. Reuse only evidence whose version/provenance matches; inventory conflicts before importing. This revision has not inspected that repository or assumed its artifacts are valid.
