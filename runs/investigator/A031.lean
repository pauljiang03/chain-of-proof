import ChainOfProof
open ChainOfProof

namespace Cert.A031

def cited : List Fact := [
  ⟨230, .webSearch, 1427134074981194, 1, 135, 126⟩ ]

def claim : Claim := Sets.searched 230

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A031

#print axioms Cert.A031.verified
