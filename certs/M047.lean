import ChainOfProof
open ChainOfProof

namespace Cert.M047

def cited : List Fact := [
  ⟨301, .webSearch, 1427133948655159, 1, 167, 159⟩,
  ⟨481, .tag, 1794614400000000, 1, 167, 229⟩ ]

def claim : Claim := .both (Sets.searched 301) (Sets.tagged 301 .obj 481 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M047

#print axioms Cert.M047.verified
