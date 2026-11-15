import ChainOfProof.Check

/-
  Census: statements about ALL the facts of one kind ("there are exactly four USB
  connection records", "none of them names this serial").

  These are a different animal from `Claim`. A `Claim` cites a few facts and stays true
  when more facts are added (`holds_mono`). A census is about the complete list, so it
  is checked against every fact of that kind, and one more fact can make it false.
  That is why it has its own type and its own checker and cannot be snapped into a
  `Claim` with `both`.

  What the kernel checks: the count, over the list in the certificate. What it cannot
  check: that the list is complete. The verifier does that, by rebuilding the list from
  the evidence file (`verifier/verify.py`). And no census says anything about events
  that left no record; the English template says so every time.

  Written like `Check.lean`: `Nat.beq`, structural recursion, single-discriminant
  matches, so a certificate depends on no axioms.
-/
namespace ChainOfProof

inductive Census where
  | total (k : Kind) (n : Nat)                           -- exactly n facts of kind k
  | distinct (k : Kind) (s : Slot) (n : Nat)             -- they name exactly n different entities in slot s
  | totalWith (k : Kind) (s : Slot) (v : Nat) (n : Nat)  -- exactly n of them have entity v in slot s
  | filesystemSetDeleted (declaration : Nat) (n : Nat) (allDeleted : Bool)
  deriving Repr

def ofKind (fs : List Fact) (k : Kind) : List Fact :=
  fs.filter fun f => f.kind == k

def addNew (x : Nat) (xs : List Nat) : List Nat :=
  match xs.any (Nat.beq x) with
  | true => xs
  | false => x :: xs

/-- The different values in a list, each once. -/
def distinctValues (xs : List Nat) : List Nat :=
  xs.foldr addNew []

/-- Membership and a source flag are one reader record; unknown flags are retained. -/
def isFilesystemMember (f : Fact) : Bool :=
  (f.kind == .filesystemMemberDeleted) ||
  (f.kind == .filesystemMemberAllocated) ||
  (f.kind == .filesystemMemberUnknown)

def filesystemMembers (fs : List Fact) (set : Nat) : List Fact :=
  fs.filter fun f => isFilesystemMember f && Nat.beq f.obj set

def filesystemDeclarations (fs : List Fact) (set : Nat) : List Fact :=
  fs.filter fun f => (f.kind == .filesystemSet) && Nat.beq f.obj set

/-- Distinct source-scoped identities, not merely distinct evidence-row IDs. -/
def uniqueMemberIdentities : List Fact → Bool
  | [] => true
  | f :: rest => !(rest.any fun other => Nat.beq f.aux other.aux) && uniqueMemberIdentities rest

def knownFilesystemFlag (f : Fact) : Bool :=
  (f.kind == .filesystemMemberDeleted) || (f.kind == .filesystemMemberAllocated)

def filesystemResult (members : List Fact) (allDeleted : Bool) : Bool :=
  if allDeleted then members.all fun f => f.kind == .filesystemMemberDeleted
  else members.any fun f => f.kind == .filesystemMemberAllocated

/-- All aggregation happens here, not in a reader-supplied summary Boolean.
    Nonempty is intentional: an empty set does not establish deletion. -/
def filesystemMembersCheck (members : List Fact) (n : Nat) (allDeleted : Bool) : Bool :=
  (Nat.blt 0 n && Nat.ble n 256) &&
  (Nat.beq members.length n &&
  (uniqueMemberIdentities members &&
  ((members.all fun f => Nat.blt 0 f.aux && knownFilesystemFlag f) &&
   filesystemResult members allDeleted)))

def filesystemSetCheck (fs : List Fact) (declaration n : Nat) (allDeleted : Bool) : Bool :=
  with1 fs declaration fun d =>
    (d.kind == .filesystemSet) &&
    ((Nat.blt 0 d.obj && Nat.blt 0 d.aux) &&
    (Nat.beq (filesystemDeclarations fs d.obj).length 1 &&
     filesystemMembersCheck (filesystemMembers fs d.obj) n allDeleted))

def counts (all : List Fact) : Census → Bool
  | .total k n => Nat.beq (ofKind all k).length n
  | .distinct k s n => Nat.beq (distinctValues ((ofKind all k).map fun f => f.get s)).length n
  | .totalWith k s v n => Nat.beq ((ofKind all k).filter fun f => Nat.beq (f.get s) v).length n
  | .filesystemSetDeleted declaration n allDeleted => filesystemSetCheck all declaration n allDeleted

private theorem andTrueParts (a b : Bool) (h : (a && b) = true) :
    a = true ∧ b = true := by
  cases a <;> cases b <;> cases h
  exact ⟨rfl, rfl⟩

/-- A successful aggregate proves the count, unique identities, every known flag,
    and either all-deleted flags or a concrete allocated-member counterexample.
    Completeness of the selected extracted set is independently rebound on replay. -/
theorem filesystemMembersCheck_sound (members : List Fact) (n : Nat) (answer : Bool)
    (h : filesystemMembersCheck members n answer = true) :
    (Nat.blt 0 n && Nat.ble n 256) = true ∧
    Nat.beq members.length n = true ∧
    uniqueMemberIdentities members = true ∧
    (members.all fun f => Nat.blt 0 f.aux && knownFilesystemFlag f) = true ∧
    filesystemResult members answer = true := by
  obtain ⟨bounds, rest⟩ := andTrueParts _ _ h
  obtain ⟨count, rest⟩ := andTrueParts _ _ rest
  obtain ⟨unique, rest⟩ := andTrueParts _ _ rest
  obtain ⟨known, result⟩ := andTrueParts _ _ rest
  exact ⟨bounds, count, unique, known, result⟩

theorem filesystemSetCheck_sound (fs : List Fact) (declaration n : Nat) (answer : Bool)
    (h : filesystemSetCheck fs declaration n answer = true) :
    ∃ d, lookup fs declaration = some d ∧ (d.kind == .filesystemSet) = true ∧
      (Nat.blt 0 d.obj && Nat.blt 0 d.aux) = true ∧
      Nat.beq (filesystemDeclarations fs d.obj).length 1 = true ∧
      filesystemMembersCheck (filesystemMembers fs d.obj) n answer = true := by
  unfold filesystemSetCheck with1 at h
  cases found : lookup fs declaration with
  | none =>
    rw [found] at h
    cases h
  | some d =>
    rw [found] at h
    obtain ⟨kind, rest⟩ := andTrueParts _ _ h
    obtain ⟨identity, rest⟩ := andTrueParts _ _ rest
    obtain ⟨unique, members⟩ := andTrueParts _ _ rest
    exact ⟨d, rfl, kind, identity, unique, members⟩

/-- Facts of other kinds do not change a census: only the listed kind is counted. -/
theorem ofKind_append (fs extra : List Fact) (k : Kind)
    (h : ∀ f ∈ extra, (f.kind == k) = false) : ofKind (fs ++ extra) k = ofKind fs k := by
  unfold ofKind
  rw [List.filter_append]
  have : extra.filter (fun f => f.kind == k) = [] := by
    apply List.filter_eq_nil_iff.mpr
    intro f hf
    simp [h f hf]
  rw [this, List.append_nil]

end ChainOfProof
