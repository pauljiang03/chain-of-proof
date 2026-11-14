import ChainOfProof
open ChainOfProof

namespace Cert.A094

def cited : List Fact := [
  ⟨192, .webSearch, 1427144278459051, 1, 102, 70⟩ ]

def claim : Claim := Sets.searched 192

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A094

#print axioms Cert.A094.verified
