import ChainOfProof
open ChainOfProof

namespace Cert.A071

def cited : List Fact := [
  ⟨169, .webSearch, 1427143530127247, 1, 101, 70⟩ ]

def claim : Claim := Sets.searched 169

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A071

#print axioms Cert.A071.verified
