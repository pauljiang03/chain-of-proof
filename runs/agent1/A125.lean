import ChainOfProof
open ChainOfProof

namespace Cert.A125

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨237, .volumeSeen, 1427205514439312, 1, 120, 31⟩ ]

def claim : Claim := Sets.openedFromRecorded 41 237

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A125

#print axioms Cert.A125.verified
