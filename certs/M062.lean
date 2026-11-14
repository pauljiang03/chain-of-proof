import ChainOfProof
open ChainOfProof

namespace Cert.M062

def cited : List Fact := [
  ⟨155, .webSearch, 1427134690237438, 1, 94, 69⟩,
  ⟨234, .tag, 1794614400000000, 1, 94, 117⟩ ]

def claim : Claim := .both (Sets.searched 155) (Sets.tagged 155 .obj 234 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M062

#print axioms Cert.M062.verified
