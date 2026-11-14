import ChainOfProof
open ChainOfProof

namespace Cert.M178

def cited : List Fact := [
  ⟨312, .cdBurn, 1427229681884909, 1, 186, 187⟩ ]

def claim : Claim := Sets.burnTrace 312

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M178

#print axioms Cert.M178.verified
