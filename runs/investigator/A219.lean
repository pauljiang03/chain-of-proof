import ChainOfProof
open ChainOfProof

namespace Cert.A219

def cited : List Fact := [
  ⟨161, .fileModified, 1418939458000000, 10000, 53, 19⟩ ]

def claim : Claim := Sets.fileModifiedAt 161

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A219

#print axioms Cert.A219.verified
