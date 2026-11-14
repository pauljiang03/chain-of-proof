import ChainOfProof
open ChainOfProof

namespace Cert.M069

def cited : List Fact := [
  ⟨165, .webSearch, 1427143427512482, 1, 89, 70⟩,
  ⟨226, .tag, 1794614400000000, 1, 89, 117⟩ ]

def claim : Claim := .both (Sets.searched 165) (Sets.tagged 165 .obj 226 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M069

#print axioms Cert.M069.verified
