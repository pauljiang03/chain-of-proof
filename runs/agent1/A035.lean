import ChainOfProof
open ChainOfProof

namespace Cert.A035

def cited : List Fact := [
  ⟨133, .webSearch, 1427134072314186, 1, 79, 70⟩ ]

def claim : Claim := Sets.searched 133

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A035

#print axioms Cert.A035.verified
