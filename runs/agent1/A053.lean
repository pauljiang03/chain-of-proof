import ChainOfProof
open ChainOfProof

namespace Cert.A053

def cited : List Fact := [
  ⟨151, .webSearch, 1427134490369135, 1, 90, 69⟩ ]

def claim : Claim := Sets.searched 151

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A053

#print axioms Cert.A053.verified
