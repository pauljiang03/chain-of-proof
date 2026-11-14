import ChainOfProof
open ChainOfProof

namespace Cert.A055

def cited : List Fact := [
  ⟨254, .webSearch, 1427134723263901, 1, 151, 125⟩ ]

def claim : Claim := Sets.searched 254

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A055

#print axioms Cert.A055.verified
