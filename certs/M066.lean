import ChainOfProof
open ChainOfProof

namespace Cert.M066

def cited : List Fact := [
  ⟨255, .webSearch, 1427134726050680, 1, 151, 125⟩,
  ⟨357, .tag, 1794614400000000, 1, 151, 195⟩ ]

def claim : Claim := .both (Sets.searched 255) (Sets.tagged 255 .obj 357 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M066

#print axioms Cert.M066.verified
