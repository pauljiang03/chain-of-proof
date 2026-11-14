import ChainOfProof
open ChainOfProof

namespace Cert.A151

def cited : List Fact := [
  ⟨161, .fileModified, 1418939458000000, 10000, 53, 19⟩ ]

def claim : Claim := Sets.fileModifiedAt 161

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A151

#print axioms Cert.A151.verified
