import ChainOfProof
open ChainOfProof

namespace Cert.A045

def cited : List Fact := [
  ⟨367, .webSearch, 1427294871248203, 1, 204, 160⟩,
  ⟨2269, .fileDownloaded, 1427294902173805, 1, 965, 1419⟩ ]

def claim : Claim := .before 367 2269

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A045

#print axioms Cert.A045.verified
