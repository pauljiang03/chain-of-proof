import ChainOfProof
open ChainOfProof

namespace Cert.A039

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨366, .volumeSeen, 1427205514439312, 1, 203, 31⟩ ]

def claim : Claim := Sets.openedFromRecorded 41 366

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A039

#print axioms Cert.A039.verified
