import ChainOfProof
open ChainOfProof

namespace Cert.A069

def cited : List Fact := [
  ⟨193, .fileModified, 1427226708000000, 2000000, 109, 69⟩ ]

def claim : Claim := Sets.fileModifiedAt 193

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A069

#print axioms Cert.A069.verified
