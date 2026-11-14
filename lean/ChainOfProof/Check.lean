import ChainOfProof.Facts
import ChainOfProof.Claim

/-
  The checker. `holds cited claim` is the whole trusted definition of "this claim is
  supported by these facts".

  It is written with `Nat.beq` / `Nat.blt` and structural recursion only. That keeps two
  properties:
    * the kernel can evaluate it by `decide`;
    * a certificate depends on no axioms at all. (`==` or `<` on `Nat` go through
      `Decidable` instances whose proofs use `propext`, which would then show up in
      `#print axioms` for every certificate.)
-/
namespace ChainOfProof

def lookup (fs : List Fact) (i : Nat) : Option Fact :=
  fs.find? (fun f => Nat.beq f.id i)

/-- `x` certainly happened before `y`: the gap exceeds both timestamp uncertainties.
    With true times in `(t - res, t + res)` this is sound for truncated, rounded and
    rounded-up clocks alike. -/
def precedes (x y : Fact) : Bool :=
  Nat.blt (x.t + x.res + y.res) y.t

def holds (fs : List Fact) : Claim → Bool
  | .before a b =>
    match lookup fs a, lookup fs b with
    | some x, some y => precedes x y
    | _, _ => false
  | .sameDevice u m =>
    match lookup fs u, lookup fs m with
    | some x, some y =>
      x.kind == .usbInsert && y.kind == .volumeMount && Nat.beq x.obj y.obj
    | _, _ => false
  | .onVolume l m =>
    match lookup fs l, lookup fs m with
    | some x, some y =>
      x.kind == .lnkTarget && y.kind == .volumeMount && Nat.beq x.aux y.aux
    | _, _ => false
  | .copied c m =>
    match lookup fs c, lookup fs m with
    | some x, some y =>
      x.kind == .fileCreated && y.kind == .fileModified
        && Nat.beq x.obj y.obj && Nat.beq x.aux y.aux && precedes y x
    | _, _ => false
  | .both c d => holds fs c && holds fs d

/-- Per-atom verdicts, for feedback to the agent when a claim is rejected.
    Diagnostic only: the certificate is the `holds … = true` theorem, not this. -/
def explain (fs : List Fact) (c : Claim) : List String :=
  c.atoms.map fun a => s!"{if holds fs a then "ok  " else "FAIL"} {repr a}"

end ChainOfProof
