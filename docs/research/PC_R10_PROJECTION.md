# R10 minimal squad projection and independent inventory

Status: **inventory only; no real squad projection or new production admission**.
This lane preserves every v1-v5 meaning and serialized byte. No Rust module,
command, save/profile version, fixture allowlist or UI member list is added.

## Existing supported information

The [R7 schema-3 projection](PC_R7_EFFECTIVE_PLAN.md) embeds the unchanged
registry fixture and ordinary mapping/bank provenance. Its 911-byte real
projection has club/manager IDs, counts, selected plan and hashes; it contains
no squad members. R8 independently found sixteen -1 human mapping entries in
both admitted inputs. An empty lineup mapping does not establish an empty squad.
The current browser can display the admitted club/manager identity, registry
selection/option/guard and explicit historical lookup result only.

## Independent raw inventory

`scripts/pc_r10_projection_inventory.py` uses Python's standard library and imports
no producer, capture, fixture or oracle parser. It verifies exact retained
image/heap or complete fresh sparse-capture pins before reading. It bounds
32-bit addresses, file sizes, sparse region lengths/count, nonoverlap, count
multiplication and complete club/staff/mapping/context extents. It independently
finds exactly one reciprocal ordinary human-manager binding and checks ordinary
club IDs against indices. Output has hashes/aggregate counts only, with exclusive
creation and private mode; no names, raw records, IDs or native pointers are emitted.
It is a research inventory, not a decoder admitted by production.

Candidate fields are club records of 581 bytes, staff records of 110 bytes,
club+0xd7 fifty DWORD slots, staff ID at +0, staff+0x39 club link and staff+0x61
player link. Pinned Bosman `include/database.h` and `src/cm3/database.c` corroborate
labels as hypotheses only (GPL code is not copied). Lane B independently locates
an official fifty-slot counting loop at 0090d429..0090d459 and an assignment
caller at 0076263b..0076266a that compares staff+0x39 to the manager's club before
00896a90. Those static facts do not qualify a complete squad or object lifetime.

Both source inventories agree with lane A's independent extraction:

| Candidate observation | Retained | Fresh |
| --- | ---: | ---: |
| Total fifty slots / nonzero DWORDs | 50 / 50 | 50 / 50 |
| Table-aligned staff links | 48 | 48 |
| Outside/unaligned links | 2 | 2 |
| Values equal unsigned -1 among fifty | 0 | 0 |
| Duplicate pointers / aligned staff ID mismatch | 0 / 0 | 0 / 0 |
| Aligned staff+0x39 differs from human club | 5 | 5 |
| Aligned nonnull staff+0x61 links | 48 | 48 |
| Reciprocal aligned ID/non-null-player candidates | 43 | 43 |
| Player-link first byte captured | 48 | 0 |
| All twenty mapping entries equal signed -1 | 20 | 20 |

The two invalid links are **not** established sentinels. The five association
mismatches are **not** labeled loans. Filtering these seven entries would not
produce a qualified complete squad. First-byte coverage is not object extent,
allocation lifetime or permission to decode a player record. Fresh sparse state
has no first-byte coverage at any of these player links. Retained coverage alone
does not establish lifetime. No player gameplay attributes are decoded; the later retained extent check reads player record IDs only.

Immutable private attempts `pc-r10-projection-inventory-20261025-a1`, `-a2` and `-a3`
retain receipts. A1 lacked a minus-one counter; A2 adds that discriminating
observation without replacing A1; A3 inventories all twenty mapping entries after B confirms original bounds. No emulation, capture, build or original process
was run. [The sanitized inventory record](evidence/pc-r10-projection-inventory-v1.json)
binds exact script and private output identities. Five optimized-Python mechanical
controls catch overlap/duplicates, missing/cross-region reads, signedness/width,
address overflow/negative size and unsupported dimensions. Synthetic control
success does not qualify real data. Lane C cannot solely admit its own output.

## Proposed transport, not frozen for implementation

The lead explicitly deferred production coding until raw membership semantics
and original linked-state lifetime are established independently. A future
`squad_projection` schema 1 would carry only source/specimen/capture/build and
projection identities, ordinary club ID and manager staff ID, ordered actual
membership slots with stable staff IDs, and the exact qualified signed mapping.
The transport must distinguish all twenty structural mapping entries from the narrower qualified action domain; B may freeze assignment at slot zero only.
A squad-array index is not a football position. No names, ratings, eligibility,
player attributes or football rules are proposed. Display labels must explicitly
say staff ID and source origin, with synthetic examples kept separate.

Before freezing: establish exact count/sentinel/association semantics and complete
read-set extents; distinguish squad membership from assignment eligibility;
validate duplicate/dangling/unaligned links, signed sentinel rules and reciprocal
relationships; bind input/build/specimen and canonical projection hashes; obtain
independent raw extraction and separate admission review. Hashes cannot replace
those layout/semantic checks. If new mutable state is needed, the lead must freeze
an explicit new compatibility profile/version and preserve v1-v5 without migration.
Malformed/hybrid/source-relabel imports must reject atomically. No fixture generated
by this lane is eligible for self-admission.

The actionable blocker is the complete original-evidenced member/assignment
contract and independently admitted projection, including linked-state lifetime
where the chosen command/readback needs it. B may qualify a smaller meaningful
assignment using genuine eligible staff without dereferencing player data; that
would require an explicit narrowed contract and still cannot silently establish a
complete squad. A/B own any separately reviewed minimally expanded capture. Until
then the real squad/lineup/save/reopen milestone remains open.

A further standalone retained structural check uses candidate player globals
00ae23c4/00ae236c and hypothesized 70-byte stride: a complete 504,980-byte
table is captured with no ID/index mismatch; all 48 aligned candidate member
links reach aligned full records with matching player IDs. This supplies extent
and identity evidence, not a constructor/load/free or backlink qualification.
B must decide and document whether its original no-player-dereference command
can freeze an immutable initialized domain; no such judgment is made here.
