import ChainOfProof
open ChainOfProof

namespace Cert.A064

def cited : List Fact := [
  ⟨263, .webSearch, 1427143497831177, 1, 156, 126⟩ ]

def claim : Claim := Sets.searched 263

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A064

#print axioms Cert.A064.verified
