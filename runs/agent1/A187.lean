import ChainOfProof
open ChainOfProof

namespace Cert.A187

def cited : List Fact := [
  ⟨147, .webSearch, 1427134400892344, 1, 87, 70⟩,
  ⟨49, .lnkTarget, 1427230050485174, 1, 23, 39⟩ ]

def claim : Claim := .before 147 49

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A187

#print axioms Cert.A187.verified
