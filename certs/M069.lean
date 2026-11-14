import ChainOfProof
open ChainOfProof

namespace Cert.M069

def cited : List Fact := [
  ⟨335, .webSearch, 1427143427512482, 1, 179, 160⟩,
  ⟨476, .tag, 1794614400000000, 1, 179, 229⟩ ]

def claim : Claim := .both (Sets.searched 335) (Sets.tagged 335 .obj 476 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M069

#print axioms Cert.M069.verified
