import ChainOfProof
open ChainOfProof

namespace Cert.M065

def cited : List Fact := [
  ⟨254, .webSearch, 1427134723263901, 1, 151, 125⟩,
  ⟨357, .tag, 1794614400000000, 1, 151, 195⟩ ]

def claim : Claim := .both (Sets.searched 254) (Sets.tagged 254 .obj 357 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M065

#print axioms Cert.M065.verified
