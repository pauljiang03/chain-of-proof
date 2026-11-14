import ChainOfProof
open ChainOfProof

namespace Cert.A077

def cited : List Fact := [
  ⟨175, .webSearch, 1427144110333084, 1, 104, 70⟩ ]

def claim : Claim := Sets.searched 175

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A077

#print axioms Cert.A077.verified
