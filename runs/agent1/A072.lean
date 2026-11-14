import ChainOfProof
open ChainOfProof

namespace Cert.A072

def cited : List Fact := [
  ⟨170, .webSearch, 1427143530137247, 1, 101, 70⟩ ]

def claim : Claim := Sets.searched 170

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A072

#print axioms Cert.A072.verified
