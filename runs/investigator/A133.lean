import ChainOfProof
open ChainOfProof

namespace Cert.A133

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨367, .volumeSeen, 1427205683393024, 1, 203, 31⟩ ]

def claim : Claim := Sets.openedFromRecorded 41 367

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A133

#print axioms Cert.A133.verified
