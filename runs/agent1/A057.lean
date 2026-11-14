import ChainOfProof
open ChainOfProof

namespace Cert.A057

def cited : List Fact := [
  ⟨155, .webSearch, 1427134690237438, 1, 94, 69⟩ ]

def claim : Claim := Sets.searched 155

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A057

#print axioms Cert.A057.verified
