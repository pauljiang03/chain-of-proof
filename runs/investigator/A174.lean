import ChainOfProof
open ChainOfProof

namespace Cert.A174

def cited : List Fact := [
  ⟨127, .fileCreated, 1427297313647604, 1, 45, 4⟩ ]

def claim : Claim := Sets.fileCreatedAt 127

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A174

#print axioms Cert.A174.verified
