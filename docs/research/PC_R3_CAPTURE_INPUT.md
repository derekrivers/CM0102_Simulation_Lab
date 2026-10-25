# Private captured club input recovery

The [sanitized receipt](evidence/pc-r3-club-capture-v1.json) binds a retained
instrumented Bosman runtime snapshot to a private three-club projection. The
snapshot includes actual club records, nonnull manager staff pointers, tactical
context, both plan banks and mapping rows. No source executable, snapshot,
club/staff record, save, game name or private fixture is redistributed.

This capture uses **older Bosman revision
`f9583098d39c77ac6982a5aa9daec56d74454531`**, with its instrumented binary and
observation object independently hashed. It is distinct from the current
`144ed82c248228c7769c6785899527eae5b33c3d` execution platform and from an
original Windows process. The original specimen identity is the official
3.9.68 SHA-256 recorded in the receipt. The retained capture receipt says
capture-only, successful exit, and records one match-engine entry observation.
No new replay or original process was launched for this recovery.

The older private input tree was rehashed against all 760 entries of the exact
clean official manifest; all match. This verifies the retained tree now. It is
not a contemporaneously sealed proof that the older runtime consumed those
same bytes. The immutable snapshot, older capture receipt, compiled binary and
instrumentation object remain separate identities; this bounded extraction
does not upgrade them to current-platform calibration or original-process
parity. The first earlier capture, whose stack bounds were corrected later,
is not used.

`scripts/recover_private_club_capture.py` reads only hash-pinned source files.
All pointer reads stay within the image or heap. It validates full club/staff
table extents and both `count * 6371` plan-bank extents. It chooses the first
three ordinary club rows with a nonnull staff-table-aligned manager pointer,
matching staff row ID below `staff_count - 16`, and an existing signed mapping
selection within the first bank. Selection values come directly from mapping
rows; none is invented. Names are read through bounded terminated fields and
remain private. The private `selected.json` also retains addresses and record
hashes for the separately reviewed original-instruction bridge.

The browser fixture schema is version 1 with `origin: captured-bosman`, source
capture identity, specimen identity, club/staff counts, ordinary club limit,
first/second bank counts, and three club projections (ID, private name,
manager ID, private name, existing selected plan). Its exact canonical UTF-8
encoding uses sorted keys, compact separators and unescaped Unicode; SHA-256
and length are in the public receipt. This fingerprint binds an input, not an
editable production database importer or original save format.

`source_capture_sha256` is the SHA-256 of the canonical `capture_sources`
identity object in the receipt: relative artifact labels, lengths and hashes.
It is not a claim that a single source file has that digest. Tactical context,
banks and mapping have their own length/hash identities. Manager-pointer
semantics and setter/resolver behavior need the separate original-instruction
qualification; the extraction script only establishes structural state.

Private invocation (substitute operator-local external paths):

```sh
python3 scripts/recover_private_club_capture.py \
  --capture /private/retained-capture \
  --clean-tree /private/retained-clean-tree \
  --clean-manifest /private/clean.manifest.tsv \
  --private-output /private/new-output \
  --public-receipt /private/new-public-receipt.json
```

Outputs must not already exist. Private files are written mode 0600 in a new
mode 0700 directory. Public output contains identities, lengths, counts,
schema and structural results only. Keep the private output outside Git.

Verification: real pinned input extraction passed twice with an unchanged
660-byte fixture fingerprint. Five redistributable controls pass via
`PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_recover_private_club_capture.py`:
wrong length/content identity, symlink input, pointer boundary/overflow,
unterminated/control-character names, and canonical fingerprint ordering.
