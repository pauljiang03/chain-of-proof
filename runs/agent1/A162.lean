import ChainOfProof
open ChainOfProof

namespace Cert.A162

def cited : List Fact := [
  ⟨150, .webSearch, 1427134451977428, 1, 89, 70⟩,
  ⟨226, .tag, 1794614400000000, 1, 89, 117⟩ ]

def claim : Claim := Sets.tagged 150 .obj 226 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A162

#print axioms Cert.A162.verified
