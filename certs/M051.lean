import ChainOfProof
open ChainOfProof

namespace Cert.M051

def cited : List Fact := [
  ⟨142, .webSearch, 1427134171496372, 1, 82, 70⟩,
  ⟨224, .tag, 1794614400000000, 1, 82, 117⟩ ]

def claim : Claim := .both (Sets.searched 142) (Sets.tagged 142 .obj 224 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M051

#print axioms Cert.M051.verified
