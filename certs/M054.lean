import ChainOfProof
open ChainOfProof

namespace Cert.M054

def cited : List Fact := [
  ⟨242, .webSearch, 1427134355567263, 1, 142, 126⟩,
  ⟨363, .tag, 1794614400000000, 1, 142, 195⟩ ]

def claim : Claim := .both (Sets.searched 242) (Sets.tagged 242 .obj 363 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M054

#print axioms Cert.M054.verified
