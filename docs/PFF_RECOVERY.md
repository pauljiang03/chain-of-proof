# Explicit PFF recovery observations

`extractor.pff_recovery` reads one explicitly selected, captured PST or OST file.
It does not run during the retained-message walk. The native parser runs in a
separate process and opens its own file handle with read-only access. No Python
`pypff` object is cast to a native pointer.

The current adapter accepts the reviewed installed libpff build only:

- API version: `20261030`.
- Shared-library SHA-256:
  `9d8f26e1e116d9aa727889aa8d2604a4a49fe1332e2ef73b404baea7a9fea266`.

The parent and child both check the library hash. The child checks the version and
declares the argument and return types for every C function used. Another build
requires a source/API review and an updated pin; version text alone is not enough.

## Run it

Use an exact captured file, with the image, exhibit and original artifact path from
its capture receipt. The output directory must not exist. Example synthetic names:

```sh
python -m extractor.pff_recovery \
  --source /captures/mailbox.ost \
  --output /results/mailbox-recovery \
  --image disk.E01 --exhibit PC \
  --artifact 'C:\Users\Example\Mail\mailbox.ost' \
  --source-snapshot base-volume --input-variant primary
```

Only specify `base-volume` and `primary` if the capture actually has those origins.
Omitted origin axes remain `unknown`. For a selected VSS store, pass its explicit
`vss:<UUID>` snapshot identity. The API allows lower or higher explicit budgets:

```python
from extractor.pff_recovery import Limits, recover_file

receipt = recover_file(captured_path, new_output_directory, provenance,
                       examined_at_utc_microseconds, limits=Limits())
```

`provenance` must identify `image` and `exhibit`. Include `artifact` or `source_path`
when the original path is known. `examined_at_utc_microseconds` must be positive.
It is examination time, not a recovered message's event time.

The adapter copies the selected regular file into the new output directory,
checks that the source did not change during the copy, and hashes the exact bytes.
It rejects symbolic links, a missing PFF signature and files over the input budget.
The parser reads the copy. Neither the selected file nor the image is opened for
writing. The capture is rehashed by the child before and after parsing, and by the
parent before emission.

## What the output means

The native call uses recovery flags `0`. It does not enable ignore-allocation or
fragment scanning. It enumerates the library's recovered-item list, not its
separate orphan list. Only the library's email item type is accepted initially.

Two typed roles are available:

| Role | Exact property |
| --- | --- |
| `mail.recovered.subject_unicode` | `0x0037`, with type `PT_UNICODE` (`0x001F`) |
| `mail.recovered.body_unicode` | `0x1000`, with type `PT_UNICODE` (`0x001F`) |

Text uses strict UTF-16LE decoding. One final storage NUL is removed. Literal empty
text and whitespace remain; missing properties are not filled. Odd-length data,
invalid surrogates, embedded/repeated NULs, other encodings, and duplicate requested
properties within or across an item's record sets reject that item's content.
HTML, RTF, codepage conversion and S/MIME decoding are not part of this adapter.

Every attribute has `source_variant=parser-recovery`. The original input variant is
also retained, and is part of the subject identity. Image, exhibit and snapshot
remain bound to the source. The subject binds the original path, exact container
hash, library hash, recovery index, item identifier/type and record-set index.
Properties in different record sets therefore cannot silently form a tuple.
Provenance adds the entry index, property/value types, raw length and raw SHA-256.
`worker.json` retains the raw property bytes as base64 for independent inspection.
These public APIs do not provide physical byte offsets for recovered properties;
the reader does not invent them.

`facts.json` contains typed observations, not a deletion or purge conclusion. A
completed receipt means that this bounded operation returned and its output passed
validation. It does not establish message authorship, delivery, allocation state,
when or whether a message was deleted, or recovery completeness. Zero items is not
evidence that no deleted messages exist. In particular, libpff's recovery entry
point can clear allocation-table read errors internally, so a successful return
cannot independently establish an allocation claim.

## Bounds and failure behavior

Defaults are 256 MiB input; 5,000 recovered items; 64 record sets per item and
100,000 total; 4,096 entries per set and 2,000,000 total; 1 MiB per text property and
8 MiB aggregate property bytes; 32 MiB aggregate output, excluding the source copy;
30 seconds CPU; 45 seconds wall time; and 1 GiB process address/data limits where
the platform supports them. The native scan has no item-limit argument, so process
limits apply before it returns its count. Limits are checked again during traversal.

The child sets available CPU, address-space, data-size, file-size and core-dump
limits. The receipt records which controls the platform accepted and which were
unavailable; OS acceptance is not a guarantee of identical memory enforcement on
all platforms. The parent kills and reaps the subprocess on wall timeout. Worker
output has a separate half-budget cap. Source capture, worker output and aggregate
published output each have explicit byte checks.

The parent validates the complete worker response before creating any attributes:
source/library identity, count reconciliation, unique item/property locators,
property types, raw lengths, hashes and Unicode. A crash, timeout, invalid response,
budget error or changed source produces a failed `receipt.json`, no `facts.json`,
and no partial observations. Unvalidated worker output is removed. Unsupported
message properties instead produce item-specific issues in a completed receipt;
other unambiguous items can still be observed.

## Public API references

- [libpff public C API](https://github.com/libyal/libpff/blob/main/include/libpff.h.in):
  file ownership, recovery enumeration, record sets and raw property access.
- [Flags and item types](https://github.com/libyal/libpff/blob/main/include/libpff/definitions.h.in).
- [MAPI property types](https://github.com/libyal/libpff/blob/main/include/libpff/mapi.h).
- [Native file recovery implementation](https://github.com/libyal/libpff/blob/main/libpff/libpff_file.c):
  allocation-table error handling.

Run focused validation with `python -m unittest tests.test_pff_recovery -v`.
Synthetic fixtures test exact property preservation, ambiguity rejection, scope
separation, budget failures, process crashes/timeouts and a real native parse of an
invalid synthetic PFF. They do not use case answers or private reference material.
