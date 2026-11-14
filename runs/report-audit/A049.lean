import ChainOfProof
open ChainOfProof

namespace Cert.A049

def cited : List Fact := [
  ⟨192, .fileModified, 1427223570611170, 1, 44, 4⟩ ]

def claim : Claim := Sets.fileModifiedAt 192

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A049

#print axioms Cert.A049.verified
