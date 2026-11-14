import ChainOfProof
open ChainOfProof

namespace Cert.A282

def cited : List Fact := [
  ⟨289, .webSearch, 1427231210726427, 1, 167, 125⟩,
  ⟨290, .webSearch, 1427294804752905, 1, 168, 126⟩ ]

def claim : Claim := .before 289 290

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A282

#print axioms Cert.A282.verified
