import ChainOfProof
open ChainOfProof

namespace Cert.M073

def cited : List Fact := [
  ⟨366, .webSearch, 1427294814471205, 1, 203, 160⟩,
  ⟨475, .tag, 1794614400000000, 1, 203, 229⟩ ]

def claim : Claim := .both (Sets.searched 366) (Sets.tagged 366 .obj 475 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M073

#print axioms Cert.M073.verified
