import ChainOfProof.Facts
import ChainOfProof.Claim

/-
  The checker. `holds cited claim` is the whole trusted definition of "this claim is
  supported by these facts".

  It is written with `Nat.beq` / `Nat.blt`, structural recursion and single-discriminant
  matches only. That keeps two properties:
    * the kernel can evaluate it by `decide`;
    * a certificate depends on no axioms at all. (`decide (a < b)`, `max`, and a
      two-discriminant `match … | _, _ => …` each pull `propext` into the definition,
      and it then shows up in `#print axioms` for every certificate.)
-/
namespace ChainOfProof

def lookup (fs : List Fact) (i : Nat) : Option Fact :=
  fs.find? (fun f => Nat.beq f.id i)

/-- `x` certainly happened before `y`: the gap exceeds both timestamp uncertainties.
    With true times in `(t - res, t + res)` this is sound for truncated, rounded and
    rounded-up clocks alike. -/
def precedes (x y : Fact) : Bool :=
  Nat.blt (x.t + x.res + y.res) y.t

/-- Look up one cited fact and test it; `false` if the id is not cited. -/
def with1 (fs : List Fact) (a : Nat) (k : Fact → Bool) : Bool :=
  match lookup fs a with
  | none => false
  | some x => k x

/-- Look up two cited facts and test them; `false` if either id is not cited. -/
def with2 (fs : List Fact) (a b : Nat) (k : Fact → Fact → Bool) : Bool :=
  with1 fs a fun x => with1 fs b fun y => k x y

/-- Matching paths or volume serials do not establish one file occurrence. -/
def sameFileOccurrence (x y : Fact) : Bool :=
  x.occurrence.complete && y.occurrence.complete && x.occurrence == y.occurrence

def holds (fs : List Fact) : Claim → Bool
  | .is f k => with1 fs f fun x => x.kind == k
  | .val f s v => with1 fs f fun x => Nat.beq (x.get s) v
  | .link a sa b sb => with2 fs a b fun x y => Nat.beq (x.get sa) (y.get sb)
  | .before a b => with2 fs a b precedes
  | .sameFileOccurrence a b => with2 fs a b sameFileOccurrence
  | .both c d => holds fs c && holds fs d

/-- Per-brick verdicts, for feedback to the agent when a claim is rejected.
    Diagnostic only: the certificate is the `holds … = true` theorem, not this. -/
def explain (fs : List Fact) (c : Claim) : List String :=
  c.atoms.map fun a => s!"{if holds fs a then "ok  " else "FAIL"} {repr a}"

end ChainOfProof
