import ChainOfProof
open ChainOfProof

namespace Cert.A175

def cited : List Fact := [
  ⟨194, .fileModified, 1427297314552404, 1, 45, 4⟩ ]

def claim : Claim := Sets.fileModifiedAt 194

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A175

#print axioms Cert.A175.verified
