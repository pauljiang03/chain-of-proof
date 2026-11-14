import ChainOfProof
open ChainOfProof

namespace Cert.M044

def cited : List Fact := [
  ⟨224, .webSearch, 1427133918131407, 1, 132, 125⟩,
  ⟨358, .tag, 1794614400000000, 1, 132, 195⟩ ]

def claim : Claim := .both (Sets.searched 224) (Sets.tagged 224 .obj 358 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M044

#print axioms Cert.M044.verified
