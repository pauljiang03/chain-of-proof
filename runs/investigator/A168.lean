import ChainOfProof
open ChainOfProof

namespace Cert.A168

def cited : List Fact := [
  ⟨192, .fileModified, 1427223570611170, 1, 44, 4⟩ ]

def claim : Claim := Sets.fileModifiedAt 192

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A168

#print axioms Cert.A168.verified
