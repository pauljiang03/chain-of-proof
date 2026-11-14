import ChainOfProof
open ChainOfProof

namespace Cert.M065

def cited : List Fact := [
  ⟨328, .webSearch, 1427134723263901, 1, 185, 159⟩,
  ⟨479, .tag, 1794614400000000, 1, 185, 229⟩ ]

def claim : Claim := .both (Sets.searched 328) (Sets.tagged 328 .obj 479 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M065

#print axioms Cert.M065.verified
