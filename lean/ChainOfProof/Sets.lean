import ChainOfProof.Claim

/-
  Sets: named compositions of primitive bricks. Each one is a forensic rule.

  A set cannot make the checker accept something false about the facts: it only
  combines primitive checks. What a set *means* lives in its English template and
  strength label (`checker/claims.py`), and those need human review.
  Add each set here and in `checker/claims.py` together.
-/
namespace ChainOfProof.Sets

/-- R1+R2 (strong): USB source record `u` and volume mapping `m` name the same device serial. -/
def usbMountedAs (u m : Nat) : Claim :=
  .both (.is u .usbInsert) (.both (.is m .volumeMount) (.link u .obj m .obj))

/-- R3 (strong): LNK `l` targets a file on the volume recorded by mapping `m`. -/
def openedFromMount (l m : Nat) : Claim :=
  .both (.is l .lnkTarget) (.both (.is m .volumeMount) (.link l .aux m .aux))

/-- R4 (heuristic): one complete scoped native file occurrence has a creation
    timestamp after its modification timestamp. No copying action is proved. -/
def copiedHere (c m : Nat) : Claim :=
  .both (.is c .fileCreated)
    (.both (.is m .fileModified)
      (.both (.sameFileOccurrence c m)
        (.both (.link c .obj m .obj) (.both (.link c .aux m .aux) (.before m c)))))

/-- R5 (strong): deletion record `d` is later than event `x`. -/
def deletedAfter (d x : Nat) : Claim :=
  .both (.is d .fileDeleted) (.before x d)

/-- R1+R7 (strong): USB record `u` and device examination `d` name the same device serial. -/
def deviceHolds (u d : Nat) : Claim :=
  .both (.is u .usbInsert) (.both (.is d .volumeOnDevice) (.link u .obj d .obj))

/-- R3+R7 (strong): LNK `l` targets the volume found on the examined device `d`. -/
def openedFromDevice (l d : Nat) : Claim :=
  .both (.is l .lnkTarget) (.both (.is d .volumeOnDevice) (.link l .aux d .aux))

/-- R3+R6 (strong): LNK `l` targets a volume this PC's registry recorded as `s`. -/
def openedFromRecorded (l s : Nat) : Claim :=
  .both (.is l .lnkTarget) (.both (.is s .volumeSeen) (.link l .aux s .aux))

/-- R6+R7 (strong): recorded volume serials match. Serial equality does not
    establish volume or physical-device identity, including for cloned volumes. -/
def recordedOnDevice (s d : Nat) : Claim :=
  .both (.is s .volumeSeen) (.both (.is d .volumeOnDevice) (.link s .aux d .aux))

/-- R8 (heuristic): two recorded volumes carry the same label. -/
def sameLabel (a b : Nat) : Claim :=
  .both (.is a .volumeSeen) (.both (.is b .volumeSeen) (.link a .obj b .obj))

/-- R1+R13 (strong): USB and recovery-area examination records carry matching
    recorded device identifiers. Physical-device identity is not established. -/
def deviceExamined (u d : Nat) : Claim :=
  .both (.is u .usbInsert) (.both (.is d .unallocatedOnDevice) (.link u .obj d .obj))

/-- R10+R13 (strong): file-creation and recovery-area examination records carry
    matching recovery-area labels. The same source area/device is not established. -/
def recoveredOnDevice (c d : Nat) : Claim :=
  .both (.is c .fileCreated) (.both (.is d .unallocatedOnDevice) (.link c .aux d .aux))

/-- Single-fact sets assert the cited row's kind. `usbConnected` names a USB source
    record, not the moment of connection. -/
def usbConnected (u : Nat) : Claim := .is u .usbInsert
/-- A retained shortcut target, not a file-open event. -/
def opened (l : Nat) : Claim := .is l .lnkTarget
def searched (w : Nat) : Claim := .is w .webSearch
def fileCreatedAt (c : Nat) : Claim := .is c .fileCreated
def fileModifiedAt (m : Nat) : Claim := .is m .fileModified
def fileDeletedAt (d : Nat) : Claim := .is d .fileDeleted
/-- Retained message metadata; no transport, delivery, authorship or reading predicate. -/
def emailed (e : Nat) : Claim := .is e .emailSent
def burnTrace (b : Nat) : Claim := .is b .cdBurn

def settingRecorded (x : Nat) : Claim := .is x .systemSetting
def accountRecorded (x : Nat) : Claim := .is x .accountSeen
def sessionRecorded (x : Nat) : Claim := .is x .sessionEvent
/-- Registration/installer record; its timestamp retains the source's declared meaning. -/
def programInstalledAt (x : Nat) : Claim := .is x .programInstalled
/-- An application observation. It cannot stand in for the typed execution roles. -/
def programRan (x : Nat) : Claim := .is x .programRun
def visited (x : Nat) : Claim := .is x .webVisit
def downloaded (x : Nat) : Claim := .is x .fileDownloaded
def typedInSearchBox (x : Nat) : Claim := .is x .localSearch
def cloudEvent (x : Nat) : Claim := .is x .cloudFile
def noteFound (x : Nat) : Claim := .is x .noteText
def folderRecorded (x : Nat) : Claim := .is x .folderOpened
def renamed (x : Nat) : Claim := .is x .fileRenamed
def fileRecorded (x : Nat) : Claim := .is x .fileSeen
def shadowCopyMade (x : Nat) : Claim := .is x .shadowCopy
def contentHashed (x : Nat) : Claim := .is x .fileContent

/-- R29 (strong): a journal record carrying a removal flag, not deletion onset or wiping. -/
def fileRemovedAt (x : Nat) : Claim := .is x .fileRemoved

/-- R30 (strong): the UDF file-set descriptor's recording timestamp on a physical disc.
    It does not state that formatting or burning completed at that time. -/
def volumeRecordedAt (x : Nat) : Claim := .is x .volumeRecorded

/-- R31 (strong): a journal record carrying a creation flag, not a filesystem timestamp. -/
def fileCreationRecordedAt (x : Nat) : Claim := .is x .fileCreationRecorded

/-- R32: names and parent references as observed in the NTFS journal. -/
def journalNamed (x : Nat) : Claim := .is x .journalName
def journalParentRecorded (x : Nat) : Claim := .is x .journalParent
def journalRemovalObserved (x : Nat) : Claim := .is x .journalRemoval

/-- R33: a child path observation constrained by intact journal intervals and directory names. -/
def journalPathAt (x : Nat) : Claim := .is x .journalPath

/-- A direct name and a byte-bounded path observation have the same scoped file identity. -/
def journalPathForFile (n p : Nat) : Claim :=
  .both (.is n .journalName) (.both (.is p .journalPath) (.link n .aux p .aux))

/-- Two separately timed names denote the same scoped file-record identity. -/
def sameJournalFile (a b : Nat) : Claim :=
  .both (.is a .journalName) (.both (.is b .journalName) (.link a .aux b .aux))

/-- A later removal flag refers to the identity of an earlier name observation.
    It does not say the earlier path was removed, or that content was wiped. -/
def removedFilePreviouslyNamed (n r : Nat) : Claim :=
  .both (.is n .journalName) (.both (.is r .journalRemoval)
    (.both (.link n .aux r .aux) (.before n r)))

/-- Join a child name, its parent reference, and a directory name. Each observation
    keeps its own timestamp; this is not presence at an alias at a different time. -/
def journalChildNamedDirectory (c p d : Nat) : Claim :=
  .both (.is c .journalName) (.both (.is p .journalParent) (.both (.is d .journalName)
    (.both (.link c .aux p .obj) (.link p .aux d .aux))))

/-- R10+R30: a filesystem creation timestamp follows a UDF descriptor timestamp
    and their recorded volume serials match. Volume identity is not established;
    distinct or cloned volumes may share a serial. No completed-write assertion. -/
def createdAfterVolumeRecord (c v : Nat) : Claim :=
  .both (.is c .fileCreated)
    (.both (.is v .volumeRecorded)
      (.both (.link c .aux v .aux) (.before v c)))

/-- R28 (strong): two content records carry the same hash. -/
def sameContent (a b : Nat) : Claim :=
  .both (.is a .fileContent) (.both (.is b .fileContent) (.link a .aux b .aux))

/-- The entity in slot `s` of fact `f` carries tag `tagId`, by tag fact `g`. -/
def tagged (f : Nat) (s : Slot) (g tagId : Nat) : Claim :=
  .both (.is g .tag) (.both (.val g .aux tagId) (.link g .obj f s))

/-- R34: three typed source rows share one attribute identity. Role/value kinds
    are fixed by the reviewed compiler catalog, never inferred from value text. -/
def recordedAttribute (s r v : Nat) (roleKind valueKind : Kind) : Claim :=
  .both (.is s .attributeSubject) (.both (.is r roleKind) (.both (.is v valueKind)
    (.both (.link s .obj r .obj) (.link s .obj v .obj))))

/-- R34: two complete attributes are recorded for the exact same scoped subject.
    This does not identify a human or turn configuration into observed use. -/
def attributesSameSubject (s r v s' r' v' : Nat) (rk vk rk' vk' : Kind) : Claim :=
  .both (recordedAttribute s r v rk vk)
    (.both (recordedAttribute s' r' v' rk' vk') (.link s .aux s' .aux))

/-- A typed reference accepted only through its actual subject, role and value rows.
    The compiler supplies the reviewed role/value kinds, never source strings. -/
structure AttributeRef where
  subject : Nat
  role : Nat
  value : Nat
  roleKind : Kind
  valueKind : Kind

/-- R34: one atomic public tuple composes existing typed-attribute and subject-link
    checks. The public parser bounds the total to 2–8 distinct approved roles;
    independent replay applies the same bound before generating this term. -/
def attributeTuple (first : AttributeRef) : List AttributeRef → Claim
  | [] => recordedAttribute first.subject first.role first.value first.roleKind first.valueKind
  | next :: rest => .both
      (attributesSameSubject first.subject first.role first.value
        next.subject next.role next.value first.roleKind first.valueKind next.roleKind next.valueKind)
      (attributeTuple first rest)

/-- R34: same-subject attributes of one declared value type contain equal encoded
    values. For image checks the compiler fixes logical/acquisition roles and algorithm. -/
def attributeValuesAgree (s r v s' r' v' : Nat) (rk rk' vk : Kind) : Claim :=
  .both (attributesSameSubject s r v s' r' v' rk vk rk' vk) (.link v .aux v' .aux)

end ChainOfProof.Sets
