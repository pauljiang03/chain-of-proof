import ChainOfProof
open ChainOfProof

namespace Cert.M045

def cited : List Fact := [
  ⟨129, .webSearch, 1427133919638342, 1, 76, 69⟩,
  ⟨230, .tag, 1794614400000000, 1, 76, 117⟩ ]

def claim : Claim := .both (Sets.searched 129) (Sets.tagged 129 .obj 230 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M045

#print axioms Cert.M045.verified
