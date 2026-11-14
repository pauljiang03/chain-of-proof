import ChainOfProof
open ChainOfProof

namespace Cert.M073

def cited : List Fact := [
  ⟨196, .webSearch, 1427294814471205, 1, 113, 70⟩,
  ⟨225, .tag, 1794614400000000, 1, 113, 117⟩ ]

def claim : Claim := .both (Sets.searched 196) (Sets.tagged 196 .obj 225 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M073

#print axioms Cert.M073.verified
