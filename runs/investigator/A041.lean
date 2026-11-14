import ChainOfProof
open ChainOfProof

namespace Cert.A041

def cited : List Fact := [
  ⟨240, .webSearch, 1427134227643461, 1, 140, 126⟩ ]

def claim : Claim := Sets.searched 240

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A041

#print axioms Cert.A041.verified
