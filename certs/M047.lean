import ChainOfProof
open ChainOfProof

namespace Cert.M047

def cited : List Fact := [
  ⟨131, .webSearch, 1427133948655159, 1, 77, 69⟩,
  ⟨231, .tag, 1794614400000000, 1, 77, 117⟩ ]

def claim : Claim := .both (Sets.searched 131) (Sets.tagged 131 .obj 231 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M047

#print axioms Cert.M047.verified
