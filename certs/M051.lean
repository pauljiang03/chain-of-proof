import ChainOfProof
open ChainOfProof

namespace Cert.M051

def cited : List Fact := [
  ⟨238, .webSearch, 1427134171496372, 1, 138, 126⟩,
  ⟨352, .tag, 1794614400000000, 1, 138, 195⟩ ]

def claim : Claim := .both (Sets.searched 238) (Sets.tagged 238 .obj 352 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M051

#print axioms Cert.M051.verified
