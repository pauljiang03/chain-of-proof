import ChainOfProof
open ChainOfProof

namespace Cert.M036

def cited : List Fact := [
  ⟨54, .lnkTarget, 1427230874336063, 1, 23, 40⟩ ]

def claim : Claim := Sets.opened 54

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M036

#print axioms Cert.M036.verified
