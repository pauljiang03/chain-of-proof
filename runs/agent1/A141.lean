import ChainOfProof
open ChainOfProof

namespace Cert.A141

def cited : List Fact := [
  ⟨85, .fileCreated, 1427222920734358, 1, 44, 4⟩ ]

def claim : Claim := Sets.fileCreatedAt 85

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A141

#print axioms Cert.A141.verified
