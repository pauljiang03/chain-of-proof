import ChainOfProof
open ChainOfProof

namespace Cert.M044

def cited : List Fact := [
  ⟨298, .webSearch, 1427133918131407, 1, 166, 159⟩,
  ⟨480, .tag, 1794614400000000, 1, 166, 229⟩ ]

def claim : Claim := .both (Sets.searched 298) (Sets.tagged 298 .obj 480 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M044

#print axioms Cert.M044.verified
