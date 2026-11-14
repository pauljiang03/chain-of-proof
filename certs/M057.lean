import ChainOfProof
open ChainOfProof

namespace Cert.M057

def cited : List Fact := [
  ⟨320, .webSearch, 1427134451977428, 1, 179, 160⟩,
  ⟨476, .tag, 1794614400000000, 1, 179, 229⟩ ]

def claim : Claim := .both (Sets.searched 320) (Sets.tagged 320 .obj 476 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M057

#print axioms Cert.M057.verified
