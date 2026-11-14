import ChainOfProof
open ChainOfProof

namespace Cert.A111

def cited : List Fact := [
  ⟨253, .webSearch, 1427134710872763, 1, 151, 125⟩ ]

def claim : Claim := Sets.searched 253

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A111

#print axioms Cert.A111.verified
