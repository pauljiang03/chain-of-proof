import ChainOfProof
open ChainOfProof

namespace Cert.A107

def cited : List Fact := [
  ⟨363, .webSearch, 1427231210726427, 1, 201, 159⟩,
  ⟨364, .webSearch, 1427294804752905, 1, 202, 160⟩ ]

def claim : Claim := .before 363 364

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A107

#print axioms Cert.A107.verified
