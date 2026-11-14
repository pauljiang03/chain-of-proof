import ChainOfProof
open ChainOfProof

namespace Cert.A069

def cited : List Fact := [
  ⟨167, .webSearch, 1427143497831177, 1, 100, 70⟩ ]

def claim : Claim := Sets.searched 167

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A069

#print axioms Cert.A069.verified
