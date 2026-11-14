import ChainOfProof
open ChainOfProof

namespace Cert.A040

def cited : List Fact := [
  ⟨138, .webSearch, 1427134079890207, 1, 80, 70⟩ ]

def claim : Claim := Sets.searched 138

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A040

#print axioms Cert.A040.verified
