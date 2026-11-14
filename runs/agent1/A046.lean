import ChainOfProof
open ChainOfProof

namespace Cert.A046

def cited : List Fact := [
  ⟨144, .webSearch, 1427134227643461, 1, 84, 70⟩ ]

def claim : Claim := Sets.searched 144

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A046

#print axioms Cert.A046.verified
