import ChainOfProof
open ChainOfProof

namespace Cert.A198

def cited : List Fact := [
  ⟨110, .fileCreated, 1427205579580000, 10000, 94, 69⟩,
  ⟨172, .fileModified, 1421435424000000, 2000000, 94, 69⟩ ]

def claim : Claim := Sets.copiedHere 110 172

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A198

#print axioms Cert.A198.verified
