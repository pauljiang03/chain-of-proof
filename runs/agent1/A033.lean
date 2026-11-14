import ChainOfProof
open ChainOfProof

namespace Cert.A033

def cited : List Fact := [
  ⟨131, .webSearch, 1427133948655159, 1, 77, 69⟩ ]

def claim : Claim := Sets.searched 131

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A033

#print axioms Cert.A033.verified
