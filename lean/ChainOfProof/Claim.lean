import ChainOfProof.Facts

/-
  Claim: the brick IR. Four primitive checks and one way to snap them together.

  Every `Nat` naming a fact is a fact id. Two bricks are joined only by `link`
  (same entity in two studs) or by citing the same fact, so a value reaches the
  report only through a cited fact. `val` compares a stud to a constant and is
  meant for tag ids.
-/
namespace ChainOfProof

inductive Claim where
  | is     (f : Nat) (k : Kind)                        -- fact f has kind k
  | val    (f : Nat) (s : Slot) (v : Nat)              -- a stud of f equals a constant
  | link   (a : Nat) (sa : Slot) (b : Nat) (sb : Slot) -- same entity in two studs
  | before (a b : Nat)                                 -- a happened before b, beyond uncertainty
  | both   (c d : Claim)                               -- snap two claims together
  deriving Repr

/-- The primitive bricks of a claim, left to right. Used for per-brick diagnostics. -/
def Claim.atoms : Claim → List Claim
  | .both c d => c.atoms ++ d.atoms
  | c => [c]

end ChainOfProof
