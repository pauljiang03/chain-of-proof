import ChainOfProof
open ChainOfProof

namespace Cert.M063

def cited : List Fact := [
  ⟨156, .webSearch, 1427134695855272, 1, 94, 69⟩,
  ⟨234, .tag, 1794614400000000, 1, 94, 117⟩ ]

def claim : Claim := .both (Sets.searched 156) (Sets.tagged 156 .obj 234 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M063

#print axioms Cert.M063.verified
