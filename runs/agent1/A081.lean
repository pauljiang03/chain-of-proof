import ChainOfProof
open ChainOfProof

namespace Cert.A081

def cited : List Fact := [
  ⟨179, .webSearch, 1427144118330597, 1, 106, 70⟩ ]

def claim : Claim := Sets.searched 179

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A081

#print axioms Cert.A081.verified
