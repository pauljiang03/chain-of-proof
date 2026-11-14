import ChainOfProof
open ChainOfProof

namespace Cert.A090

def cited : List Fact := [
  ⟨188, .webSearch, 1427144157439657, 1, 109, 70⟩ ]

def claim : Claim := Sets.searched 188

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A090

#print axioms Cert.A090.verified
