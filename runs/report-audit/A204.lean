import ChainOfProof
open ChainOfProof

namespace Cert.A204

def cited : List Fact := [
  ⟨311, .cdBurn, 1427229681619709, 1, 190, 185⟩,
  ⟨304, .emailSent, 1427231109679000, 1000000, 183, 174⟩ ]

def claim : Claim := .before 311 304

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A204

#print axioms Cert.A204.verified
