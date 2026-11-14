/-
  Facts: the evidence vocabulary. Rows are produced by the extractor, never by an LLM.

  This file is the contract between the Data and Lean roles. Changing `Kind` or `Fact`
  means changing `extractor/schema.sql` and `checker/facts.py` in the same commit.

  Meaning of `obj` / `aux` per kind (both are interned entity ids):

    kind          obj                      aux
    usbInsert     device serial            0
    volumeMount   device serial            volume serial
    lnkTarget     target path              volume serial the target lives on
    fileCreated   file path                volume serial
    fileModified  file path                volume serial
    fileDeleted   original path            volume serial
    webSearch     query string             browser / profile
    emailSent     subject                  "from A to B", as the mailbox records them
    cdBurn        the trace found          where it was found
    tag           tagged entity            tag id
    volumeSeen    volume label             volume serial   (the PC's registry or a shortcut recorded it)
    volumeOnDevice device serial           volume serial   (read from the seized device's image)
    unallocatedOnDevice device serial      area id         (the seized device's image has directory
                                                            entries left outside any current file;
                                                            recovered fileCreated / fileModified rows
                                                            carry the same area id in `aux`)
    systemSetting setting name             its value       (t = when the setting was written, or
                                                            the moment the setting itself records)
    accountSeen   account name or id       what it is an account of (a Windows local account,
                                                            a cloud service, an e-mail client)
    sessionEvent  logon / logoff / startup / shutdown / ...   the account, or 0 for the machine
    programInstalled program name          version
    programRun    executable name          full path       (one row per recorded run time)
    webVisit      URL                      browser
    fileDownloaded saved path              source URL
    localSearch   text typed               where it was typed
    cloudFile     file name or cloud path  "<service>: <event>"
    noteText      text of the note         application
    folderOpened  folder path              artifact that records it (shell bag, ...)
    fileRenamed   old name                 new name
    fileSeen      file path                secondary artifact that records it (search index,
                                                            thumbnail cache, shadow copy, ...)
    shadowCopy    shadow copy id           volume
    fileContent   file path                "sha256:<hex>"  (t = when the image was examined)
    fileRemoved   file path                volume serial   (t = journal record carrying FILE_DELETE;
                                                            not exact deletion onset or a wiping assertion)
    volumeRecorded physical disc id        volume serial   (t = UDF file-set descriptor recording
                                                            time, not examination or write completion)
    fileCreationRecorded file path         volume serial   (t = journal record carrying FILE_CREATE;
                                                            not a filesystem creation timestamp)
    journalName   observed name/path       scoped NTFS identity (image, full volume serial,
                                                            file record and sequence; journal observation time)
    journalParent scoped child identity    scoped parent identity (journal observation time)
    journalRemoval observed name/path      scoped NTFS identity (removal-flag observation,
                                                            not onset, every alias removed, or wiping)
-/
namespace ChainOfProof

inductive Kind where
  | usbInsert | volumeMount | lnkTarget
  | fileCreated | fileModified | fileDeleted
  | webSearch | emailSent | cdBurn
  | tag
  | volumeSeen | volumeOnDevice
  | unallocatedOnDevice
  | systemSetting | accountSeen | sessionEvent | programInstalled | programRun
  | webVisit | fileDownloaded | localSearch | cloudFile | noteText
  | folderOpened | fileRenamed | fileSeen | shadowCopy
  | fileContent
  | fileRemoved | volumeRecorded
  | fileCreationRecorded
  | journalName | journalParent | journalRemoval
  deriving DecidableEq, Repr

structure Fact where
  id   : Nat    -- row id in the evidence DB
  kind : Kind
  t    : Nat    -- UTC microseconds since the Unix epoch
  res  : Nat    -- timestamp uncertainty in µs: the true time lies within (t - res, t + res)
  obj  : Nat    -- interned primary entity
  aux  : Nat    -- interned secondary entity
  deriving Repr

/-- A stud: one of a fact's two entity slots. -/
inductive Slot where
  | obj | aux
  deriving DecidableEq, Repr

def Fact.get (f : Fact) : Slot → Nat
  | .obj => f.obj
  | .aux => f.aux

end ChainOfProof
