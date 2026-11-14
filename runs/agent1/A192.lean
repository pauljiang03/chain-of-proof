import ChainOfProof
open ChainOfProof

namespace Cert.A192

def cited : List Fact := [
  ⟨193, .webSearch, 1427231210726427, 1, 111, 69⟩,
  ⟨194, .webSearch, 1427294804752905, 1, 112, 70⟩ ]

def claim : Claim := .before 193 194

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A192

#print axioms Cert.A192.verified
