import ChainOfProof
open ChainOfProof

namespace Cert.A116

def cited : List Fact := [
  ⟨251, .webSearch, 1427134690237438, 1, 150, 125⟩,
  ⟨362, .tag, 1794614400000000, 1, 150, 195⟩ ]

def claim : Claim := Sets.tagged 251 .obj 362 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A116

#print axioms Cert.A116.verified
