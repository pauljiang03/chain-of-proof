import ChainOfProof
open ChainOfProof

namespace Cert.A099

def cited : List Fact := [
  ⟨375, .emailSent, 1427203557000000, 1000000, 214, 206⟩,
  ⟨8981, .fileRenamed, 1427204991896881, 1, 12620, 12621⟩ ]

def claim : Claim := .before 375 8981

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A099

#print axioms Cert.A099.verified
