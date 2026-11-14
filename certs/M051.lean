import ChainOfProof
open ChainOfProof

namespace Cert.M051

def cited : List Fact := [
  ⟨312, .webSearch, 1427134171496372, 1, 172, 160⟩,
  ⟨474, .tag, 1794614400000000, 1, 172, 229⟩ ]

def claim : Claim := .both (Sets.searched 312) (Sets.tagged 312 .obj 474 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M051

#print axioms Cert.M051.verified
