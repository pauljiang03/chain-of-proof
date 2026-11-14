import ChainOfProof
open ChainOfProof

namespace Cert.M069

def cited : List Fact := [
  ⟨261, .webSearch, 1427143427512482, 1, 145, 126⟩,
  ⟨354, .tag, 1794614400000000, 1, 145, 195⟩ ]

def claim : Claim := .both (Sets.searched 261) (Sets.tagged 261 .obj 354 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M069

#print axioms Cert.M069.verified
