import ChainOfProof
open ChainOfProof

namespace Cert.M058

def cited : List Fact := [
  ⟨321, .webSearch, 1427134490369135, 1, 180, 159⟩,
  ⟨469, .tag, 1794614400000000, 1, 180, 229⟩ ]

def claim : Claim := .both (Sets.searched 321) (Sets.tagged 321 .obj 469 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M058

#print axioms Cert.M058.verified
