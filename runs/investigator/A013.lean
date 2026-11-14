import ChainOfProof
open ChainOfProof

namespace Cert.A013

def cited : List Fact := [
  ⟨212, .webSearch, 1427038079597811, 1, 127, 125⟩ ]

def claim : Claim := Sets.searched 212

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A013

#print axioms Cert.A013.verified
