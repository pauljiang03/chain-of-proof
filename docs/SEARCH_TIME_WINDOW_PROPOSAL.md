# Opt-in recorded Search timestamp windows

Development capability only. `agent.timestamp_predicates` is connected to the
answer requirement gate through `attribute_timestamp_conditions`. No real
question mapping, Lean statement, source reader or matching rule is changed.

An explicitly reviewed public requirement may include this condition in its
`attribute_timestamp_conditions` list:

```json
{
  "mode": "recorded_instant_half_open_v1",
  "role": "search.index.date_modified",
  "start": "2015-03-22T04:00:00Z",
  "stop": "2015-03-24T04:00:00Z"
}
```

Those bounds correspond to **both local days March 22 and March 23**, if the public
policy explicitly selects that interpretation and `America/New_York`. The prompt
alone does not decide interval inclusivity. `local_day_interval` requires explicit
first day, exclusive stop day and IANA zone; it rejects ambiguous or nonexistent
local midnights. Freeze the timezone database for a reproducible run. Unknown or
naive source offsets are rejected; they are not resolved from the report zone.

The exact integer parser preserves all seven FILETIME fractional digits. It
accepts an explicit UTC instant or signed offset, rejects unknown `-00:00`, more
than seven fraction digits, leap seconds and malformed/out-of-range clocks.
`recorded_in_interval` requires the exact approved role and checks `[start, stop)`;
other roles are unsupported. Invalid values or policies raise `ValueError` and
must become binding refusal, never guard bypass, default time or value repair.

The gate requires a unique typed DateModified value in the same claim part and
refuses malformed timestamps. An activated mapping must also require DateModified,
literal ItemUrl and reviewed native IE category/store in one checked attribute tuple.
Keep the extractor's existing subject identity, including source origin,
container hash, ESE table, identifier-column name, DocID/WorkID and row ordinal.
Duplicate IDs and rows from different containers cannot be joined. Retain original
timestamp text and provenance in the projected certificate; membership supplies a
filter result, not a new timestamp or user-action statement.

Native IE store/category availability in the actual source is **not established**.
A synthetic `iehistory` value, URL suffix, shortcut file or path substring does
not establish that availability. Do not activate the Q44 mapping until source
selection, actual native category and this explicit local-day policy are reviewed.
Even then the claim describes an indexed record and its recorded DateModified;
it does not establish a person's browser use or when that use occurred.

Controls cover exact 100 ns boundaries, equivalent offsets, reversed ordering in
the DST fold, 23/25-hour local days, ambiguous/nonexistent midnight, wrong roles,
invalid zones, malformed dates, inverted bounds and independent datetime controls.
Independent source-to-checker/replay/projection tests remain the fourth session's
lane after integration. This helper alone adds no scored or certified coverage.
