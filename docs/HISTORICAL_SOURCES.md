# Explicit historical source API

`extractor.historical_sources` inventories VSS sources and compares selected file
content without publishing facts, changing images, inferring actors, or issuing
proof verdicts. It also selects exact UDF descriptor states from an existing
optical survey. The caller supplies image/exhibit identity and owns target lifetime.

## Standalone command

The module CLI opens the explicit image and writes one new JSON observation
receipt. It does not publish facts or run a proof checker:

```sh
python -m extractor.historical_sources discover \
  --image /evidence/pc.E01 --exhibit PC --out ./vss-inventory.json

python -m extractor.historical_sources compare \
  --image /evidence/pc.E01 --exhibit PC \
  --copy-uuid '<explicit copy UUID from the inventory>' \
  --path 'C:\Windows\win.ini' --out ./vss-comparison.json
```

Repeat `--path` for additional exact paths. `--volume-identity` accepts the
inventory's exact identity string if needed to disambiguate a copy UUID. Every
VSS resource limit is available under its hyphenated name, such as
`--max-files 8 --max-file-bytes 16777216 --max-total-bytes 33554432`. There is no
implicit snapshot selector. Existing outputs, including symlinks and files
created after the initial check, are refused through exclusive creation. The
output directory must already exist. Image files are never opened for writing.

The receipt records the exact request, observation start/completion times, the
recomputed SHA-256 of this module's source file, parser package versions, canonical
input paths, and each image/EWF segment's size, device/inode and modification/change
timestamps. Segment identities are checked again after observation. This does
not establish content immutability or acquisition authenticity. Code hashing
covers this module on disk, not all dependency code. Input image/segment hashes
are **not recomputed** by this command; the selected complete file streams are
hashed by the comparison API.

Optional `--intake-config /path/to/intake-config.json` checks the configuration's
schema and JSON digest, its image path/exhibit mapping, and the current segment
names/sizes. The configuration file's SHA-256 is recomputed and recorded.
Segment SHA-256 values from that configuration are retained with the explicit
status `declared_by_intake_not_recomputed`. Without a configuration, segment
hashes remain null with status `not_recomputed`. Configuration-declared segment
hashes are never presented as a new verification of the image, and prior facts
are neither opened nor verified by this option.

Exit code 0 means the requested observations completed, including legitimate
absence. Exit code 1 means the new receipt contains incomplete, unsupported,
unreadable or limited observations. Invalid arguments, unknown/ambiguous
selectors, changed input identity, and setup/output errors exit 2. Source or
selector validation failures do not publish a guessed comparison. The CLI is
VSS-only; it does not start an optical scan or reconstruct optical sessions.

## VSS inventory and selection

```python
from dissect.target import Target
from extractor.historical_sources import Limits, discover_vss, compare_versions

target = Target.open(image_path)
inventory = discover_vss(target, {
    "image": image_path.name,
    "exhibit": explicit_exhibit_id,
    "source_snapshot": "base-volume",
    "source_variant": "primary",
}, limits=Limits(max_files=8, max_file_bytes=16 * 1024 * 1024))
public_inventory = inventory.as_dict()

# The UUID must come from an explicit caller selection in this inventory.
report = compare_versions(inventory, explicit_copy_uuid, [r"C:\folder\file.txt"])
```

`discover_vss` reads catalog and linked store-information metadata only. Each
source retains canonical `copy_uuid`, `store_uuid`, `set_uuid`, exact unsigned
`creation_filetime`, seven-digit UTC `created_at`, catalog/header offsets, mounted
drive identity, full 64-bit NTFS serial, VSS volume/store-volume UUIDs, and available
partition offset/size/number. `volume_identity` is a deterministic JSON identity
including the caller's image and exhibit. It is not an acquisition hash; callers
must retain their existing intake image/segment hash bindings.

Catalog provenance remains `source_snapshot="base-volume"`. A copy UUID named by
base metadata does not establish that snapshot content was opened. The catalog
creation time is not a file creation, modification, deletion, or transfer time.

`select_vss(inventory, snapshot_id, volume_identity=None)` accepts a UUID, UUID
string, or `vss:<UUID>`. It returns the matching source handle. It never chooses
latest/earliest, accepts a time alias, treats a store UUID as a copy UUID, or
silently chooses among duplicates. Ambiguity requires the exact
`volume_identity`; duplicate copies within that same volume remain ambiguous.
Incomplete discovery refuses selection because an omitted source could change
uniqueness. No NTFS filesystem is `unsupported`, not a claim that VSS was absent.

## File version observations

`compare_versions` takes the same explicit selector and a nonempty bounded list
of drive-qualified paths. All paths must address the selected source's single
recorded drive mapping. It rejects relative, wildcard, UNC, alternate-stream,
cross-drive, duplicate, and ambiguous mount paths. It opens fresh NTFS views of
base and the selected VSS stream, checks the opened full NTFS serial, checks each
directory-index reference's record and sequence number, and refuses reparse
traversal or unallocated records. The content scope is the complete logical
unnamed `$DATA` stream, excluding slack and alternate streams.

Each side reports its own `path`, provenance and status. Complete observations
include `sha256`, `bytes_read`, logical size, MFT segment/sequence, and raw plus
seven-digit UTC `$STANDARD_INFORMATION` timestamps. Snapshot content is scoped
`source_snapshot="vss:<copy UUID>"`; the separate selected-source catalog record
still has base-volume origin. Input source variants are preserved. Unknown or
mixed input source scope is rejected, not upgraded.

| Status | Meaning |
| --- | --- |
| `present` | Complete selected logical stream read and hashed. |
| `absent` | Exact directory-index path lookup found no entry in that namespace. |
| `unreadable` | Parsing or content I/O failed, including a short stream or unavailable index. |
| `unsupported` | Structure or binding cannot be interpreted safely, including stale/deleted records, reparse traversal, or cross-volume VSS storage without an explicit binding. |
| `limit_exceeded` | An explicit bound prevented complete observation. |

`comparison` is `same_content` or `different_content` only when both sides are
`present`, based on complete SHA-256 plus byte length. Otherwise it is
`not_comparable`. Matching size/timestamps alone cannot establish equality. A
timestamp change alone cannot establish different content. Snapshot-only
presence does not establish a deletion event, transfer direction, or an actor.
The API returns hashes and provenance, not file contents or a full-image copy.

## Resource bounds and ownership

Default limits are 16 NTFS volumes, 256 catalog entries/linked blocks, 64 selected
source candidates, 32 requested files, 64 MiB per logical file, 256 MiB combined
content across both sides, 16 MiB catalog metadata reads, 512 MiB requested I/O per
comparison, 100,000 underlying read calls, and 128 path components. Catalog
preflight detects cyclic links and nonempty entries hidden after an empty entry
before invoking Dissect's eager catalog constructor. Normal empty linked padding
is accepted. Bounds are configurable positive integers.

Each directory component lookup additionally permits at most 128 index nodes
and 4,096 entries per node (`max_index_nodes`, `max_index_entries`, also exposed
as CLI flags). It tracks visited child VCNs before invoking Dissect's cached
index-buffer lookup. A cached self-cycle or longer cycle therefore cannot bypass
the bound by avoiding further I/O. Node materialization is bounded separately.
The lookup preserves the primary parser's uppercase `FILE_NAME` comparison and
exact-match/child-routing decisions; malformed keys, missing/end-entry errors,
and unsorted names are refused instead of reporting absence. Cycles/malformed
nodes are `unsupported`, exhausted caps are `limit_exceeded`, and only a completed
exact no-match becomes `absent`. Unrelated parser `KeyError`s remain unreadable.

Underlying read limits include lazy snapshot block-map/reconstruction work as
well as file metadata. Short/failed underlying reads are charged by requested
length. Logical content budget counts received bytes, including failed reads;
incomplete streams receive no complete-content hash. The requested-I/O figure
counts wrapper reads, including nested reads during reconstruction, and is not a
physical device traffic measurement.

Targets must already be open. Target discovery, EWF decompression internals, and
prior optical surveys are outside this module's operation budgets. It does not
close caller-owned targets or volume streams. A comparison closes its own
snapshot/file streams. Inventory handles and their underlying seekable streams
are for sequential use; do not share one handle between concurrent comparisons.

## Optical descriptor selection and exact remaining gap

The existing `extractor.optical.Udf._versions` parser exposes safe state locators:
VAT sector plus file-set descriptor (FSD) sector. `discover_optical(survey, common,
limits=...)` indexes those already parsed states, retaining FSD-byte SHA-256,
volume serial, raw recorded timestamp bytes, named/deleted entry counts, and
the exact `udf:vat=<sector|none>:fsd=<sector>` identity. `common` must explicitly
identify `optical-image` scope. `select_optical(inventory, descriptor_id)` selects
exactly that state; the returned `OpticalSource` holds `metadata` and `version`.
Two VATs that reference the same FSD remain distinct states. No historical state
is relabeled as the current primary state. Parser errors, inconsistent version
links, missing descriptor bytes, or exceeded admission bounds prevent selection.
The incoming whole-image survey must have `source_variant="primary"`; alternate,
recovered, unknown, or already selected descriptor variants are rejected before
provenance is assigned. This prevents distinct input variants from collapsing
into the same VAT/FSD source identity.

This API does not initiate `optical.survey`, whose `Udf.load` currently scans the
disc to discover retained descriptors. Admission defaults to 64 states, 100,000
retained entries, and 16 MiB retained VAT/FSD metadata. Existing survey content
methods are not new bounded optical comparison methods. VSS `compare_versions`
does not accept optical selections.

**Remaining capability gap:** selection of a coherent filesystem by optical
session number. Audited implementations are `extractor.optical.ewf_sessions`,
`extractor.optical.Udf._versions`, and `extractor.optical.Survey.session`.
`ewf_sessions` exposes acquisition flags/start sectors; `_versions` reconstructs
VAT/FSD states, and `Survey.session` assigns sector positions to acquisition
starts. They do not reconstruct a session-specific descriptor sequence. Therefore
`optical_session_capability()` returns this specific `unsupported` result and
the explicit VAT/FSD alternative. No generic placeholder or guessed “latest
session” is substituted. A separately bounded on-demand optical scan and optical
content comparison remain outside this API.

## Validation

`python -m unittest tests.test_historical_sources` exercises real synthetic UDF
descriptor bytes, raw VSS catalog blocks, and NTFS parser-interface fixtures.
Controls cover exact/ambiguous/unknown identifiers, mixed origins, catalog
cycles, hidden entries, stale/deleted NTFS references, content versus time
changes, absent/unreadable/unsupported distinctions, and byte/file/source limits.
CLI controls also cover required arguments, exact UUID selection, input mutation,
exclusive output creation including a creation race, configuration digest and
identity mismatches, and declared versus recomputed hash status.
Directory-index regressions include the installed Dissect parser's cached
self-cycle in a timeout-contained subprocess, multi-node cycles, node/entry
caps, unsorted keys, and valid lookup parity with that primary implementation.

Read-only smoke on the supplied `pc.E01` opened explicit copy
`8f1a2a2d-ce6b-42a5-b92b-f13e65d9c2cb` on NTFS serial `C8CA0C8DCA0C7A48`:
`C:\Windows\win.ini` produced two matching 478-byte complete hashes;
`C:\Windows\System32\config\SYSTEM` produced different complete hashes for two
12,582,912-byte streams; a deliberately nonexistent path was `absent` on both
sides. The catalog retained exact FILETIME `130717690472938055`
(`2015-03-25T14:57:27.2938055Z`). A second raw-image smoke on the supplied
`4Dell Latitude CPi.E01` reported no VSS header/catalog on its NTFS volume rather
than a parser failure. These observations demonstrate source selection and do
not claim a forensic answer or universal historical coverage.

The standalone CLI was also exercised directly against `pc.E01` with its supplied
intake configuration. Both `discover` and explicit-copy `compare` exited 0;
`C:\Windows\win.ini` produced matching 478-byte hashes with distinct base/VSS
origins. The receipt lists all four EWF segments with hashes labeled as intake
declarations, plus newly recomputed configuration and module-source hashes.
