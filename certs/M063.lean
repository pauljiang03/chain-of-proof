import ChainOfProof
open ChainOfProof

namespace Cert.M063

def cited : List Fact := [
  ⟨252, .webSearch, 1427134695855272, 1, 150, 125⟩,
  ⟨362, .tag, 1794614400000000, 1, 150, 195⟩ ]

def claim : Claim := .both (Sets.searched 252) (Sets.tagged 252 .obj 362 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M063

#print axioms Cert.M063.verified
