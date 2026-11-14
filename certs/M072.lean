import ChainOfProof
open ChainOfProof

namespace Cert.M072

def cited : List Fact := [
  ⟨291, .webSearch, 1427294804771004, 1, 168, 126⟩,
  ⟨343, .tag, 1794614400000000, 1, 168, 195⟩ ]

def claim : Claim := .both (Sets.searched 291) (Sets.tagged 291 .obj 343 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M072

#print axioms Cert.M072.verified
