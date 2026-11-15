# Prospective public representation derivatives

`eval.representation_derivative.prepare(public_path, policy_path, output_dir)`
prepares a fresh public-only directory. It does not accept a reference, invoke an
investigator, score answers, rewrite native values, or authorize a comparison.
The original public file remains byte-for-byte unchanged.

The policy has exactly these keys:

```json
{
  "version": 1,
  "case_id": "new-prospective-case",
  "contract_revision": "new-prospective-revision",
  "ancestor_public_sha256": "<SHA256 of original public bytes>",
  "questions": {
    "Q4": {
      "fields": {
        "/time_zone_setting": {
          "kind": "zone-label-offset-v1",
          "label_mode": "casefold_whitespace"
        }
      },
      "source_contexts": {}
    }
  }
}
```

This example illustrates syntax, not an approved real-case policy. Both case ID
and contract revision must change. Explicit pointers must resolve to string
leaves in the public answer schema. Unknown questions, opaque or union schemas,
ambiguous wildcard rules, existing normalization, and legacy rule overlaps refuse
preparation. Existing rules are never silently removed.

Only existing `typed-representation-v1` kinds are accepted: GUID spelling,
zone label with numeric offset, and source-bound volume paths. Each path context
must supply the complete origin, NTFS serial, explicit roots, and mapping receipt
hash described in [MATCH_NORMALIZATION.md](MATCH_NORMALIZATION.md). Independent
review must establish that mapping; a hash alone does not prove it. Unused
contexts refuse. No OS aliases, fraction truncation, Unicode text changes or
native-answer conversions are added.

Public bytes are captured once and the shared validator reads a private snapshot
of those exact bytes. After validation and staging, exclusive directory creation
claims the output name. Exclusive hard links publish `questions.json`, the exact
`policy.json`, and finally `manifest.json`. The manifest is the atomic completion
marker; publication is not an atomic whole-directory operation. It binds ancestor, policy, builder,
normalizer and new-question hashes and records that separate independent
reference alignment remains required. Validation failures leave no output.
Publication failures remove only this builder's files. A process crash may leave
a partial directory without a manifest: it is unpublished and cannot be reused or
overwritten by this API. Existing destinations, including concurrent empty
directories, are never replaced.
The corresponding reference derivative and release decision belong to the
independent reference reviewer and coordinator, outside this public-only API.
