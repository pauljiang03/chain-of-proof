import ChainOfProof
open ChainOfProof

namespace Cert.A029

def cited : List Fact := [
  ⟨127, .webSearch, 1427133915865196, 1, 76, 69⟩ ]

def claim : Claim := Sets.searched 127

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A029

#print axioms Cert.A029.verified
