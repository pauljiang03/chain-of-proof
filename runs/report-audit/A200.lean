import ChainOfProof
open ChainOfProof

namespace Cert.A200

def cited : List Fact := [
  ⟨311, .cdBurn, 1427229681619709, 1, 190, 185⟩,
  ⟨44, .lnkTarget, 1427229853752619, 1, 34, 35⟩ ]

def claim : Claim := .before 311 44

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A200

#print axioms Cert.A200.verified
