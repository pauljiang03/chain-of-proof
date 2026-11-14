import ChainOfProof
open ChainOfProof

namespace Cert.A156

def cited : List Fact := [
  ⟨163, .fileModified, 1419018826000000, 10000, 18, 19⟩ ]

def claim : Claim := Sets.fileModifiedAt 163

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A156

#print axioms Cert.A156.verified
