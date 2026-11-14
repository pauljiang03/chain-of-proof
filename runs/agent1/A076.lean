import ChainOfProof
open ChainOfProof

namespace Cert.A076

def cited : List Fact := [
  ⟨174, .webSearch, 1427144108553579, 1, 103, 70⟩ ]

def claim : Claim := Sets.searched 174

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A076

#print axioms Cert.A076.verified
