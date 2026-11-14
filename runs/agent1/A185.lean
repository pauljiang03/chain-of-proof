import ChainOfProof
open ChainOfProof

namespace Cert.A185

def cited : List Fact := [
  ⟨85, .fileCreated, 1427222920734358, 1, 44, 4⟩,
  ⟨44, .lnkTarget, 1427229853752619, 1, 34, 35⟩ ]

def claim : Claim := .before 85 44

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A185

#print axioms Cert.A185.verified
