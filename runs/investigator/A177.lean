import ChainOfProof
open ChainOfProof

namespace Cert.A177

def cited : List Fact := [
  ⟨58, .lnkTarget, 1427297327141605, 1, 45, 4⟩ ]

def claim : Claim := Sets.opened 58

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A177

#print axioms Cert.A177.verified
