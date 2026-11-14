import ChainOfProof
open ChainOfProof

namespace Cert.M059

def cited : List Fact := [
  ⟨152, .webSearch, 1427134544517540, 1, 91, 69⟩,
  ⟨223, .tag, 1794614400000000, 1, 91, 117⟩ ]

def claim : Claim := .both (Sets.searched 152) (Sets.tagged 152 .obj 223 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M059

#print axioms Cert.M059.verified
