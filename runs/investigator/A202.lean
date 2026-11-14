import ChainOfProof
open ChainOfProof

namespace Cert.A202

def cited : List Fact := [
  ⟨114, .fileCreated, 1427205583520000, 10000, 98, 69⟩,
  ⟨173, .fileModified, 1421766824000000, 2000000, 98, 69⟩ ]

def claim : Claim := Sets.copiedHere 114 173

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A202

#print axioms Cert.A202.verified
