/-
  Claim: the IR the LLM writes (as JSON; `checker/claims.py` turns it into a term of this type).

  Every argument is a fact id. A claim never carries a raw value such as a volume serial:
  values reach the report only through cited facts, and two atoms are linked only by
  citing the same fact. See `Check.lean` for what each atom requires.
-/
namespace ChainOfProof

inductive Claim where
  | before     (a b : Nat)               -- a happened before b, beyond timestamp uncertainty
  | sameDevice (usb mount : Nat)         -- R1+R2: USB insert and volume mapping share a device serial
  | onVolume   (lnk mount : Nat)         -- R3: LNK target lives on the volume named by `mount`
  | copied     (created modified : Nat)  -- R4 (heuristic): created after last modified
  | both       (c d : Claim)
  deriving Repr

/-- The atoms of a claim, left to right. Used for per-atom diagnostics. -/
def Claim.atoms : Claim → List Claim
  | .both c d => c.atoms ++ d.atoms
  | c => [c]

end ChainOfProof
