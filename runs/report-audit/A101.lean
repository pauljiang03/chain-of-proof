import ChainOfProof
open ChainOfProof

namespace Cert.A101

def cited : List Fact := [
  ⟨126, .fileCreated, 1427226707220000, 10000, 109, 69⟩ ]

def claim : Claim := Sets.fileCreatedAt 126

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A101

#print axioms Cert.A101.verified
