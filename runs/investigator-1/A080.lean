import ChainOfProof
open ChainOfProof

namespace Cert.A080

def cited : List Fact := [
  ⟨386, .cdBurn, 1427229681884909, 1, 220, 221⟩,
  ⟨129, .fileCreated, 1427230482676152, 1, 34, 111⟩ ]

def claim : Claim := .before 386 129

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A080

#print axioms Cert.A080.verified
