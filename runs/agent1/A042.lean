import ChainOfProof
open ChainOfProof

namespace Cert.A042

def cited : List Fact := [
  ⟨140, .webSearch, 1427134111817280, 1, 81, 70⟩ ]

def claim : Claim := Sets.searched 140

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A042

#print axioms Cert.A042.verified
