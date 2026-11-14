import ChainOfProof
open ChainOfProof

namespace Cert.A167

def cited : List Fact := [
  ⟨155, .webSearch, 1427134690237438, 1, 94, 69⟩,
  ⟨234, .tag, 1794614400000000, 1, 94, 117⟩ ]

def claim : Claim := Sets.tagged 155 .obj 234 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A167

#print axioms Cert.A167.verified
