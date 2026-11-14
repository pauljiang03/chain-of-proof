import ChainOfProof.Facts

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

def counts (all : List Fact) : Census → Bool
  | .total k n => Nat.beq (ofKind all k).length n
  | .distinct k s n => Nat.beq (distinctValues ((ofKind all k).map fun f => f.get s)).length n
  | .totalWith k s v n => Nat.beq ((ofKind all k).filter fun f => Nat.beq (f.get s) v).length n

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
