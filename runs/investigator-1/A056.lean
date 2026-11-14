import ChainOfProof
open ChainOfProof

namespace Cert.A056

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨488, .volumeSeen, 1427205514439312, 1, 251, 31⟩,
  ⟨407, .tag, 1794614400000000, 1, 30, 231⟩,
  ⟨493, .volumeSeen, 1427230954309607, 1, 251, 253⟩ ]

def claim : Claim := .both (Sets.openedFromRecorded 41 488) (.both (Sets.tagged 41 .obj 407 231) (Sets.sameLabel 488 493))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A056

#print axioms Cert.A056.verified
