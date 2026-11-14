import ChainOfProof
open ChainOfProof

namespace Cert.A053

def cited : List Fact := [
  ⟨2290, .cloudFile, 1427142757552000, 1000, 1422, 1429⟩,
  ⟨374, .emailSent, 1427143279000000, 1000000, 213, 206⟩ ]

def claim : Claim := .before 2290 374

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A053

#print axioms Cert.A053.verified
