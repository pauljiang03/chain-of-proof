import ChainOfProof
open ChainOfProof

namespace Cert.A108

def cited : List Fact := [
  ⟨246, .webSearch, 1427134451977428, 1, 145, 126⟩,
  ⟨354, .tag, 1794614400000000, 1, 145, 195⟩ ]

def claim : Claim := Sets.tagged 246 .obj 354 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A108

#print axioms Cert.A108.verified
