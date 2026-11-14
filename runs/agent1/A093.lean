import ChainOfProof
open ChainOfProof

namespace Cert.A093

def cited : List Fact := [
  ⟨191, .webSearch, 1427144168707174, 1, 102, 70⟩ ]

def claim : Claim := Sets.searched 191

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A093

#print axioms Cert.A093.verified
