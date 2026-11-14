import ChainOfProof
open ChainOfProof

namespace Cert.A147

def cited : List Fact := [
  ⟨176, .fileModified, 1422046030000000, 10000, 52, 19⟩ ]

def claim : Claim := Sets.fileModifiedAt 176

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A147

#print axioms Cert.A147.verified
