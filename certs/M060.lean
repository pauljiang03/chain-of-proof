import ChainOfProof
open ChainOfProof

namespace Cert.M060

def cited : List Fact := [
  ⟨153, .webSearch, 1427134615783075, 1, 92, 69⟩,
  ⟨227, .tag, 1794614400000000, 1, 92, 117⟩ ]

def claim : Claim := .both (Sets.searched 153) (Sets.tagged 153 .obj 227 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M060

#print axioms Cert.M060.verified
