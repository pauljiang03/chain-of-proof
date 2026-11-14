import ChainOfProof
open ChainOfProof

namespace Cert.A020

def cited : List Fact := [
  ⟨118, .webSearch, 1427039744335028, 1, 72, 69⟩ ]

def claim : Claim := Sets.searched 118

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A020

#print axioms Cert.A020.verified
