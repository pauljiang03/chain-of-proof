import ChainOfProof
open ChainOfProof

namespace Cert.M061

def cited : List Fact := [
  ⟨250, .webSearch, 1427134634631105, 1, 149, 125⟩,
  ⟨344, .tag, 1794614400000000, 1, 149, 195⟩ ]

def claim : Claim := .both (Sets.searched 250) (Sets.tagged 250 .obj 344 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M061

#print axioms Cert.M061.verified
