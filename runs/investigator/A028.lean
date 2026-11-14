import ChainOfProof
open ChainOfProof

namespace Cert.A028

def cited : List Fact := [
  ⟨227, .webSearch, 1427133948655159, 1, 133, 125⟩ ]

def claim : Claim := Sets.searched 227

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A028

#print axioms Cert.A028.verified
