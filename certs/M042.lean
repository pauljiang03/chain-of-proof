import ChainOfProof
open ChainOfProof

namespace Cert.M042

def cited : List Fact := [
  ⟨296, .webSearch, 1427133873578434, 1, 166, 159⟩,
  ⟨480, .tag, 1794614400000000, 1, 166, 229⟩ ]

def claim : Claim := .both (Sets.searched 296) (Sets.tagged 296 .obj 480 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M042

#print axioms Cert.M042.verified
