import ChainOfProof
open ChainOfProof

namespace Cert.A059

def cited : List Fact := [
  ⟨157, .webSearch, 1427134710872763, 1, 95, 69⟩ ]

def claim : Claim := Sets.searched 157

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A059

#print axioms Cert.A059.verified
