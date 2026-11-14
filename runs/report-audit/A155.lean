import ChainOfProof
open ChainOfProof

namespace Cert.A155

def cited : List Fact := [
  ⟨164, .fileModified, 1419018826000000, 2000000, 102, 69⟩ ]

def claim : Claim := Sets.fileModifiedAt 164

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A155

#print axioms Cert.A155.verified
