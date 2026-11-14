import ChainOfProof
open ChainOfProof

namespace Cert.A106

def cited : List Fact := [
  ⟨378, .emailSent, 1427231109679000, 1000000, 217, 208⟩,
  ⟨363, .webSearch, 1427231210726427, 1, 201, 159⟩ ]

def claim : Claim := .before 378 363

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A106

#print axioms Cert.A106.verified
