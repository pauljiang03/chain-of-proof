import ChainOfProof
open ChainOfProof

namespace Cert.A212

def cited : List Fact := [
  ⟨124, .fileCreated, 1427205618410000, 10000, 108, 69⟩,
  ⟨174, .fileModified, 1421777886000000, 2000000, 108, 69⟩ ]

def claim : Claim := Sets.copiedHere 124 174

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A212

#print axioms Cert.A212.verified
