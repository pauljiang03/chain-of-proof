import ChainOfProof
open ChainOfProof

namespace Cert.A142

def cited : List Fact := [
  ⟨111, .fileModified, 1427223570611170, 1, 44, 4⟩ ]

def claim : Claim := Sets.fileModifiedAt 111

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A142

#print axioms Cert.A142.verified
