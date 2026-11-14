import ChainOfProof
open ChainOfProof

namespace Cert.A055

def cited : List Fact := [
  ⟨153, .webSearch, 1427134615783075, 1, 92, 69⟩ ]

def claim : Claim := Sets.searched 153

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A055

#print axioms Cert.A055.verified
