import ChainOfProof
open ChainOfProof

namespace Cert.M068

def cited : List Fact := [
  ⟨331, .webSearch, 1427140063009623, 1, 186, 159⟩,
  ⟨471, .tag, 1794614400000000, 1, 186, 229⟩ ]

def claim : Claim := .both (Sets.searched 331) (Sets.tagged 331 .obj 471 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M068

#print axioms Cert.M068.verified
