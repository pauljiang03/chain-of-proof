import ChainOfProof
open ChainOfProof

namespace Cert.M196

def cited : List Fact := [
  ⟨269, .fileDeleted, 1427226707117000, 1, 144, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 269

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M196

#print axioms Cert.M196.verified
