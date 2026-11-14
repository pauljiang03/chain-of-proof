import ChainOfProof
open ChainOfProof

namespace Cert.A032

def cited : List Fact := [
  ⟨231, .webSearch, 1427134074991194, 1, 135, 126⟩ ]

def claim : Claim := Sets.searched 231

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A032

#print axioms Cert.A032.verified
