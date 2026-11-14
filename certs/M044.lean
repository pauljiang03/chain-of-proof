import ChainOfProof
open ChainOfProof

namespace Cert.M044

def cited : List Fact := [
  ⟨128, .webSearch, 1427133918131407, 1, 76, 69⟩,
  ⟨230, .tag, 1794614400000000, 1, 76, 117⟩ ]

def claim : Claim := .both (Sets.searched 128) (Sets.tagged 128 .obj 230 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M044

#print axioms Cert.M044.verified
