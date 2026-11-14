import ChainOfProof
open ChainOfProof

namespace Cert.M029

def cited : List Fact := [
  ⟨47, .lnkTarget, 1427229858080231, 1, 38, 0⟩ ]

def claim : Claim := Sets.opened 47

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M029

#print axioms Cert.M029.verified
