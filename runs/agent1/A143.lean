import ChainOfProof
open ChainOfProof

namespace Cert.A143

def cited : List Fact := [
  ⟨86, .fileCreated, 1427297313647604, 1, 45, 4⟩ ]

def claim : Claim := Sets.fileCreatedAt 86

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A143

#print axioms Cert.A143.verified
