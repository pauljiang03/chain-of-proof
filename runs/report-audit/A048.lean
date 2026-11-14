import ChainOfProof
open ChainOfProof

namespace Cert.A048

def cited : List Fact := [
  ⟨125, .fileCreated, 1427222920734358, 1, 44, 4⟩ ]

def claim : Claim := Sets.fileCreatedAt 125

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A048

#print axioms Cert.A048.verified
