import ChainOfProof
open ChainOfProof

namespace Cert.M058

def cited : List Fact := [
  ⟨247, .webSearch, 1427134490369135, 1, 146, 125⟩,
  ⟨348, .tag, 1794614400000000, 1, 146, 195⟩ ]

def claim : Claim := .both (Sets.searched 247) (Sets.tagged 247 .obj 348 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M058

#print axioms Cert.M058.verified
