import ChainOfProof
open ChainOfProof

namespace Cert.A096

def cited : List Fact := [
  ⟨194, .webSearch, 1427294804752905, 1, 112, 70⟩ ]

def claim : Claim := Sets.searched 194

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A096

#print axioms Cert.A096.verified
