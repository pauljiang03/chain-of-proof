import ChainOfProof
open ChainOfProof

namespace Cert.M048

def cited : List Fact := [
  ⟨302, .webSearch, 1427133987545120, 1, 168, 159⟩,
  ⟨478, .tag, 1794614400000000, 1, 168, 229⟩ ]

def claim : Claim := .both (Sets.searched 302) (Sets.tagged 302 .obj 478 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M048

#print axioms Cert.M048.verified
