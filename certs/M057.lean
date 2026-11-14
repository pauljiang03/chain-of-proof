import ChainOfProof
open ChainOfProof

namespace Cert.M057

def cited : List Fact := [
  ⟨150, .webSearch, 1427134451977428, 1, 89, 70⟩,
  ⟨226, .tag, 1794614400000000, 1, 89, 117⟩ ]

def claim : Claim := .both (Sets.searched 150) (Sets.tagged 150 .obj 226 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M057

#print axioms Cert.M057.verified
