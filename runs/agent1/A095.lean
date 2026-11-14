import ChainOfProof
open ChainOfProof

namespace Cert.A095

def cited : List Fact := [
  ⟨193, .webSearch, 1427231210726427, 1, 111, 69⟩ ]

def claim : Claim := Sets.searched 193

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A095

#print axioms Cert.A095.verified
