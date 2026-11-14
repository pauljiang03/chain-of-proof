import ChainOfProof
open ChainOfProof

namespace Cert.A283

def cited : List Fact := [
  ⟨83, .fileCreated, 1427140547296776, 1, 66, 4⟩ ]

def claim : Claim := Sets.fileCreatedAt 83

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A283

#print axioms Cert.A283.verified
