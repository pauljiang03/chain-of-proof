import ChainOfProof
open ChainOfProof

namespace Cert.M041

def cited : List Fact := [
  ⟨221, .webSearch, 1427133820424839, 1, 132, 125⟩,
  ⟨358, .tag, 1794614400000000, 1, 132, 195⟩ ]

def claim : Claim := .both (Sets.searched 221) (Sets.tagged 221 .obj 358 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M041

#print axioms Cert.M041.verified
