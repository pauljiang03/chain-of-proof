import ChainOfProof
open ChainOfProof

namespace Cert.A175

def cited : List Fact := [
  ⟨147, .webSearch, 1427134400892344, 1, 87, 70⟩,
  ⟨30, .lnkTarget, 1427135903445366, 1, 22, 19⟩ ]

def claim : Claim := .before 147 30

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A175

#print axioms Cert.A175.verified
