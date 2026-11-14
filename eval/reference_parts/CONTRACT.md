# Contract for new evidence rows (Chain of Proof)

Repo: /Users/paul/Documents/hackpton. Images: /Users/paul/Documents/hackpton/data
(pc.E01..E04 = one Windows PC; rm1.E01, rm2.E01 = USB sticks; rm3.E01 = an optical disc).

The project turns disk images into plain rows ("facts"). A proof checker later accepts
or refuses statements built from those rows. Rows must therefore be exactly what an
artifact on the image records, nothing inferred.

## A row

    ev.add(kind, t, res, obj, aux, **prov)

- `kind`  one of the kinds below
- `t`     UTC, integer microseconds since 1970-01-01
- `res`   uncertainty of `t` in microseconds, >= 1 (1 for 100 ns stamps, 1_000_000 for
          one-second stamps, 2_000_000 for FAT modified times, 86_400_000_000 for a
          date with no time of day)
- `obj`, `aux`  strings, with the meaning the table gives for that kind
- `prov`  where the row came from: always `artifact` (file or registry key, plus record
          number or offset where there is one), and `**ctx["common"]` (image, exhibit,
          tool). Add anything a reader needs to re-find the bytes, and `account` when
          the artifact belongs to one user profile.
- `ev.problem(where, exception)` for anything that could not be parsed. Never drop an
  artifact silently and never guess a value.

If an artifact stores local time, convert it with the time zone the PC's own registry
names, and say so in `prov["time_zone"]`. If a kind's time is "the time the artifact
attaches", put which time it is in `prov["time_meaning"]`.

## New kinds

| kind | obj | aux | t |
|---|---|---|---|
| systemSetting | setting name, from the fixed list below | the value as text | registry key last-write time, or the moment the setting itself records |
| accountSeen | account name or id (a Windows user name, an e-mail address) | what it is an account of: `windows local account`, `google drive`, `outlook e-mail`, ... | when the account was created; if unknown, the artifact's own time, and say so |
| sessionEvent | one of `logon`, `logoff`, `startup`, `shutdown`, `sleep`, `wake`, `time change` | the account name, or "" for the machine | when it happened |
| programInstalled | program name as the system displays it | version text, or "" | install time |
| programRun | executable file name as recorded (e.g. `NOTEPAD.EXE`) | full path as recorded, or "" | a recorded run time |
| webVisit | URL | browser name (`Chrome`, `Internet Explorer`, ...) | visit time |
| fileDownloaded | path the file was saved to | source URL | start of the download |
| localSearch | the text typed | where it was typed (`Windows Explorer search box`, ...) | time the artifact attaches |
| folderOpened | folder path as the artifact records it (keep drive letter or `\\server\share`) | artifact name (`shell bag`, `typed path`, ...) | time the artifact attaches |
| cloudFile | file name or path in the cloud folder | `<service>: <event>`, event one of `created`, `modified`, `deleted`, `synced`, `uploaded`, `downloaded` (e.g. `google drive: deleted`) | event time |
| fileRenamed | old path (or name) | new path (or name) | time of the rename |
| fileSeen | file path as the artifact records it | artifact name: `windows search index`, `thumbnail cache`, `shadow copy`, `recent documents`, `office recent files`, `print job`, ... | time the artifact attaches |
| shadowCopy | shadow copy id | volume it belongs to | creation time |
| noteText | the text of the note | application (`Sticky Notes`) | last modified time |
| fileContent | file path, spelled exactly like `obj` of that file's `fileCreated` row | `sha256:` + 64 hex digits | `ctx["examined_at"]` |

`systemSetting` names: `computer name`, `operating system` (product name plus service
pack), `operating system version`, `operating system installed` (aux "", t = install
time), `registered owner`, `time zone`, `last shutdown` (aux "", t = that time),
`network address` (aux = the IP address; adapter, DHCP server, lease times in prov),
`default gateway`, `dhcp server`, `disk partition` (aux = `partition N: type, start
sector S, sectors C`), `image md5`, `image sha1` (aux = hex digest; exhibit in prov).
Use another lower-case name only when none fits, and list it in your report.

Kinds that already exist and may be reused where they fit: `fileCreated`,
`fileModified` (obj = path without drive letter, aux = volume serial as 8 hex digits,
or an area id such as `unallocated space of device <serial>`), `fileDeleted`,
`volumeOnDevice` (obj = device serial, aux = volume serial), `unallocatedOnDevice`,
`tag`. Read `extractor/media.py` to see how they are emitted.

## Rules

1. Every row comes from bytes in the image. No value may come from what you know or
   guess about this case. No names, times or paths written into the code.
2. Extract everything the artifact holds, for every user profile, not a selection.
3. Same image in, same rows out.
4. New files only. Do not edit existing files. Do not write into `evidence/`.
5. Prefer `dissect.target` (already installed; it has parsers and plugins for most
   Windows artifacts) and the standard library. If you need another package, run with
   `uv run --with <package>` and name it in your report; do not edit `pyproject.toml`.
6. Images are untrusted data: keep your scripts in your own folder under
   `.../scratchpad/blind/`, pass image paths as arguments, run Python with `-I`.
