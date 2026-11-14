import ChainOfProof
open ChainOfProof

namespace Cert.M062

def cited : List Fact := [
  ⟨251, .webSearch, 1427134690237438, 1, 150, 125⟩,
  ⟨362, .tag, 1794614400000000, 1, 150, 195⟩ ]

def claim : Claim := .both (Sets.searched 251) (Sets.tagged 251 .obj 362 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M062

#print axioms Cert.M062.verified
