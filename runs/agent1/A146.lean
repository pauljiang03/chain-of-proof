import ChainOfProof
open ChainOfProof

namespace Cert.A146

def cited : List Fact := [
  ⟨56, .lnkTarget, 1427297313663204, 1, 45, 4⟩ ]

def claim : Claim := Sets.opened 56

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A146

#print axioms Cert.A146.verified
