import ChainOfProof
open ChainOfProof

namespace Cert.M058

def cited : List Fact := [
  ⟨151, .webSearch, 1427134490369135, 1, 90, 69⟩,
  ⟨220, .tag, 1794614400000000, 1, 90, 117⟩ ]

def claim : Claim := .both (Sets.searched 151) (Sets.tagged 151 .obj 220 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M058

#print axioms Cert.M058.verified
