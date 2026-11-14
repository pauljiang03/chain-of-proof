import ChainOfProof
open ChainOfProof

namespace Cert.A043

def cited : List Fact := [
  ⟨141, .webSearch, 1427134134101318, 1, 82, 70⟩ ]

def claim : Claim := Sets.searched 141

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A043

#print axioms Cert.A043.verified
