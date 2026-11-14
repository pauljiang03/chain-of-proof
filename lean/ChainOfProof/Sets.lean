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

/-- The entity in slot `s` of fact `f` carries tag `tagId`, by tag fact `g`. -/
def tagged (f : Nat) (s : Slot) (g tagId : Nat) : Claim :=
  .both (.is g .tag) (.both (.val g .aux tagId) (.link g .obj f s))

end ChainOfProof.Sets
