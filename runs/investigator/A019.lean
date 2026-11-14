import ChainOfProof
open ChainOfProof

namespace Cert.A019

def cited : List Fact := [
  ⟨218, .webSearch, 1427133764343210, 1, 131, 125⟩ ]

def claim : Claim := Sets.searched 218

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A019

#print axioms Cert.A019.verified
