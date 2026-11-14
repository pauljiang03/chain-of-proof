import ChainOfProof
open ChainOfProof

namespace Cert.A097

def cited : List Fact := [
  ⟨290, .webSearch, 1427294804752905, 1, 168, 126⟩,
  ⟨343, .tag, 1794614400000000, 1, 168, 195⟩ ]

def claim : Claim := Sets.tagged 290 .obj 343 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A097

#print axioms Cert.A097.verified
