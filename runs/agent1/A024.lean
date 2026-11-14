import ChainOfProof
open ChainOfProof

namespace Cert.A024

def cited : List Fact := [
  ⟨122, .webSearch, 1427133764343210, 1, 75, 69⟩ ]

def claim : Claim := Sets.searched 122

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A024

#print axioms Cert.A024.verified
