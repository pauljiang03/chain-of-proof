import ChainOfProof
open ChainOfProof

namespace Cert.A211

def cited : List Fact := [
  ⟨123, .fileCreated, 1427205615650000, 10000, 107, 69⟩,
  ⟨175, .fileModified, 1421784300000000, 2000000, 107, 69⟩ ]

def claim : Claim := Sets.copiedHere 123 175

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A211

#print axioms Cert.A211.verified
