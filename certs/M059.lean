import ChainOfProof
open ChainOfProof

namespace Cert.M059

def cited : List Fact := [
  ⟨322, .webSearch, 1427134544517540, 1, 181, 159⟩,
  ⟨472, .tag, 1794614400000000, 1, 181, 229⟩ ]

def claim : Claim := .both (Sets.searched 322) (Sets.tagged 322 .obj 472 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M059

#print axioms Cert.M059.verified
