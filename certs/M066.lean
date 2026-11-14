import ChainOfProof
open ChainOfProof

namespace Cert.M066

def cited : List Fact := [
  ⟨329, .webSearch, 1427134726050680, 1, 185, 159⟩,
  ⟨479, .tag, 1794614400000000, 1, 185, 229⟩ ]

def claim : Claim := .both (Sets.searched 329) (Sets.tagged 329 .obj 479 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M066

#print axioms Cert.M066.verified
