# Retained mail text and SQLite WAL views

`extractor.artifact_containers` uses these readers when it validates supported
Outlook, browser and Sticky Notes containers. The existing intake reader name
remains `artifact_containers`.

## Mail text

The retained-folder traversal reads these literal MAPI fields:

| Property | Typed roles | Encoding source |
| --- | --- | --- |
| Subject, `0x0037` | `mail.message.subject_unicode`, `mail.message.subject_string8` | PT_UNICODE, or the recorded message code page |
| Body, `0x1000` | `mail.message.body_unicode`, `mail.message.body_string8` | PT_UNICODE, or the recorded Internet code page |
| HTML, `0x1013` | `mail.message.body_html` | PT_BINARY with the recorded Internet code page |

HTML stays literal markup. No browser renders it. The reader does not execute
scripts or retrieve linked resources. For STRING8 subjects, an explicit zero
message code page can use an explicit code page from the containing folder.
Missing or unsupported encodings produce a diagnostic for that property.

Properties from the same retained message share a subject that includes the
container identity, folder route, message index and PFF item identifier.
Provenance includes the record-set and property-entry locators, raw property
hash and encoding rule. Duplicate properties are rejected before their second
byte payload is read. Existing Unicode role meanings are unchanged.

These values establish what the retained properties contain. They do not, by
themselves, establish delivery, authorship or a recovered-message status.

## SQLite WAL

For a supported SQLite container, the reader checks for an exact adjacent
`-wal` file in the same opened filesystem view. It validates the WAL header,
generation salts and cumulative checksums. Only complete transactions through
the last valid commit contribute to the derived view. Uncommitted frames and
invalid tails are excluded and counted. The transient `-shm` file is unused.

The reader keeps separate hashes for the captured base database, WAL and
derived view. Its subject binds all three when a WAL exists. SQLite then opens
the derived copy with `mode=ro&immutable=1` and checks integrity and the required
application schema. Original image files are unchanged.

Sticky Notes container modification time still refers to the base file's
filesystem timestamp. It is not the WAL time or an inferred note edit time.

## Checks

```sh
python -m unittest tests.test_mail_content tests.test_sqlite_wal \
  tests.test_artifact_containers tests.test_sticky_note_fields
```

WAL tests create transactions with SQLite itself and compare damaged-tail
handling with the native SQLite reader. Mail tests cover source code pages,
literal HTML, same-message emission and ambiguous properties. Source validation
also read HTML from the supplied mailbox. The committed-WAL positive example
used a synthetic SQLite-generated fixture; the inspected real containers had
no adjacent WAL.
