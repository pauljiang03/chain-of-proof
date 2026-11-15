# Opt-in representation matching, version 1

The matcher supports an optional `typed-representation-v1` extension. No existing
public or private contract enables it in this change. Existing matching behavior
and historical artifacts are retained. The implementation does not authorize a
new experiment or resolve source, population, attribution or reference gaps.

An independently reviewed comparison derivative must declare both keys below in
each affected question's public and private `match` object. It must retain the
original reference payloads/statuses and identify a separately reviewed case and
contract revision. Those release requirements are reviewed by the coordinator
and reference author; the parser does not authenticate an ancestry declaration.

```json
{
  "normalization_profile": {
    "id": "typed-representation-v1",
    "version": 1,
    "ancestor_public_sha256": "<64 lowercase hexadecimal characters>",
    "source_contexts": {}
  },
  "normalization": {
    "version": 1,
    "fields": {
      "/identifiers/*": {"kind": "guid-v1"},
      "/zone": {"kind": "zone-label-offset-v1"}
    }
  }
}
```

This is a schema illustration, not a runnable source selection. Rules use the
existing JSON-pointer convention: `*` matches one component, and the most specific
matching rule wins. Equally specific conflicting rules refuse matching. Every
rule must address a reference scalar. Unknown keys, versions and kinds refuse
preflight. The extension rejects overlapping legacy path, timestamp, string-mode,
alias and subset rules, including container rules that could bypass a child.
Global prefix matching cannot be combined with it. Other global string modes do
not transform an opted-in typed value before or after its declared parser.

Both operands use the identical parser and context. Canonical values are compared
in memory; submissions, evidence, bindings and reference values are never rewritten.
Invalid expected values block reference validation. Invalid submitted values are
mismatches, retaining the normal missing/wrong accounting. Reports preserve raw
audit values and include the extension implementation hash when enabled. The
reference hash binds its configuration, and the pilot freeze pins the new module.
Legacy profiles do not gain an extension field. Source hashes naturally identify
the changed implementation; saved historical reports are not regenerated.

## Supported representations

- `guid-v1`: exactly 32 ASCII hex digits or 8-4-4-4-12 groups, optionally inside one
  matched brace pair. Hex case is insignificant. No whitespace, URN prefix, partial
  text, Unicode digits or byte-order reinterpretation. Distinct copy/set roles and
  source identity remain separate from textual GUID identity.
- `zone-label-offset-v1`: `<label> (<offset>)`, `<label> <offset>` or
  `(<offset>) <label>`. Offsets are UTC/GMT plus signed one/two-digit hours and
  two-digit minutes with a colon; or bare signed `HH:MM`/`HHMM`. Hours are at most
  14, minutes at most 59, hour 14 requires zero minutes, and negative zero refuses.
  Labels remain exact unless `label_mode` explicitly declares `casefold` or
  `casefold_whitespace`. Multiple offsets, empty labels and ambiguous parses refuse.
  No zone database, date, DST state, locale or abbreviation is inferred.
- `windows-volume-path-v1`: requires the complete rule
  `{"kind":"windows-volume-path-v1","context":"<id>","case_sensitive":true,
  "allow_volume_rooted":false}`. Its source context must declare one exact origin
  (`image`, `exhibit`, `source_snapshot`, `source_variant`, plus `input_source` for
  examination origins), a `volume` object with `kind: "ntfs-serial-64"` and a
  16-lowercase-hex `value`, an explicit `absolute_roots` list, and a 64-hex
  `mapping_receipt_sha256`. The independent review must establish the mapping;
  a digest string alone is not proof. Roots are concrete drives or UNC shares.
  An image-relative path requires explicit `allow_volume_rooted: true`. Arbitrary
  drives/shares are never stripped. No traversal, device namespace, ADS, wildcard,
  empty interior component, trailing dot/space, environment expansion, short-name
  alias or reparse resolution is accepted. Directory-trailing-separator status is
  preserved. Case-insensitive mode folds ASCII only; non-ASCII components remain
  exact without a reviewed source upcase table. Canonical identity retains origin
  and volume, not just a relative suffix.

Bounds are 64 source contexts, 32 roots per context, 256 field rules, pointer depth
16, input strings of 32,768 code points and at most 256 KiB UTF-8. Unicode behavior
is tied to the frozen Python runtime. Missing evidence is never manufactured by
normalization. A generic browser label is not a versioned-product alias, and a
bounded extracted executable set is not automatically the original requested
population. These remain independent review questions.

Synthetic parser/scorer tests cover symmetric spelling equivalence, wrong
identities and offsets, malformed values, origin/volume changes, foreign roots,
ambiguous/overlapping rules, raw audit retention and list multiplicity/extras.
No private expected values were used to author the implementation or tests.
