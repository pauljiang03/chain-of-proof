import ChainOfProof
open ChainOfProof

namespace Cert.A049

def cited : List Fact := [
  ⟨147, .webSearch, 1427134400892344, 1, 87, 70⟩ ]

def claim : Claim := Sets.searched 147

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A049

#print axioms Cert.A049.verified
