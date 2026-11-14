import ChainOfProof
open ChainOfProof

namespace Cert.A170

def cited : List Fact := [
  ⟨43, .lnkTarget, 1427222920812357, 1, 33, 4⟩ ]

def claim : Claim := Sets.opened 43

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A170

#print axioms Cert.A170.verified
