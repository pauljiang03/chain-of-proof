import ChainOfProof
open ChainOfProof

namespace Cert.A064

def cited : List Fact := [
  ⟨8981, .fileRenamed, 1427204991896881, 1, 12620, 12621⟩,
  ⟨109, .fileCreated, 1427205577630000, 10000, 93, 69⟩ ]

def claim : Claim := .before 8981 109

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A064

#print axioms Cert.A064.verified
