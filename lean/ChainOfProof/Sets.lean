import ChainOfProof.Claim

/-
  Sets: named compositions of primitive bricks. Each one is a forensic rule.

  A set cannot make the checker accept something false about the facts: it only
  combines primitive checks. What a set *means* lives in its English template and
  strength label (`checker/sets.py`, `Rules.md`), and those need human review.
  Adding a set means adding it here and in `checker/sets.py` in the same commit.
-/
namespace ChainOfProof.Sets

/-- R1+R2 (strong): USB insert `u` and volume mapping `m` name the same device serial. -/
def usbMountedAs (u m : Nat) : Claim :=
  .both (.is u .usbInsert) (.both (.is m .volumeMount) (.link u .obj m .obj))

/-- R3 (strong): LNK `l` targets a file on the volume recorded by mapping `m`. -/
def openedFromMount (l m : Nat) : Claim :=
  .both (.is l .lnkTarget) (.both (.is m .volumeMount) (.link l .aux m .aux))

/-- R4 (heuristic): on one volume, a path created after its last modification. -/
def copiedHere (c m : Nat) : Claim :=
  .both (.is c .fileCreated)
    (.both (.is m .fileModified)
      (.both (.link c .obj m .obj) (.both (.link c .aux m .aux) (.before m c))))

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

/-- R6+R7 (strong): the volume recorded as `s` is the one on the examined device `d`. -/
def recordedOnDevice (s d : Nat) : Claim :=
  .both (.is s .volumeSeen) (.both (.is d .volumeOnDevice) (.link s .aux d .aux))

/-- R8 (heuristic): two recorded volumes carry the same label. -/
def sameLabel (a b : Nat) : Claim :=
  .both (.is a .volumeSeen) (.both (.is b .volumeSeen) (.link a .obj b .obj))

/-- Single-fact sets: the claim is that the cited record exists and is of this kind. -/
def usbConnected (u : Nat) : Claim := .is u .usbInsert
def opened (l : Nat) : Claim := .is l .lnkTarget
def searched (w : Nat) : Claim := .is w .webSearch
def fileCreatedAt (c : Nat) : Claim := .is c .fileCreated
def fileModifiedAt (m : Nat) : Claim := .is m .fileModified

/-- The entity in slot `s` of fact `f` carries tag `tagId`, by tag fact `g`. -/
def tagged (f : Nat) (s : Slot) (g tagId : Nat) : Claim :=
  .both (.is g .tag) (.both (.val g .aux tagId) (.link g .obj f s))

end ChainOfProof.Sets
