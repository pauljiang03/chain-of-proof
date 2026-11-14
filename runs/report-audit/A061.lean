import ChainOfProof
open ChainOfProof

namespace Cert.A061

def cited : List Fact := [
  ⟨159, .fileModified, 1418746226000000, 10000, 51, 19⟩ ]

def claim : Claim := Sets.fileModifiedAt 159

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A061

#print axioms Cert.A061.verified
