import ChainOfProof
open ChainOfProof

namespace Cert.A064

def cited : List Fact := [
  ⟨162, .webSearch, 1427140099531147, 1, 97, 69⟩ ]

def claim : Claim := Sets.searched 162

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A064

#print axioms Cert.A064.verified
