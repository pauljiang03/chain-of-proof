import ChainOfProof
open ChainOfProof

namespace Cert.M027

def cited : List Fact := [
  ⟨45, .lnkTarget, 1427229854570221, 1, 36, 0⟩ ]

def claim : Claim := Sets.opened 45

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M027

#print axioms Cert.M027.verified
