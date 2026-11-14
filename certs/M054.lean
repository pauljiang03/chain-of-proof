import ChainOfProof
open ChainOfProof

namespace Cert.M054

def cited : List Fact := [
  ⟨146, .webSearch, 1427134355567263, 1, 86, 70⟩,
  ⟨235, .tag, 1794614400000000, 1, 86, 117⟩ ]

def claim : Claim := .both (Sets.searched 146) (Sets.tagged 146 .obj 235 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M054

#print axioms Cert.M054.verified
