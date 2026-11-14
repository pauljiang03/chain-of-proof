import ChainOfProof
open ChainOfProof

namespace Cert.M026

def cited : List Fact := [
  ⟨44, .lnkTarget, 1427229853752619, 1, 34, 35⟩ ]

def claim : Claim := Sets.opened 44

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M026

#print axioms Cert.M026.verified
