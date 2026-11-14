import ChainOfProof
open ChainOfProof

namespace Cert.M052

def cited : List Fact := [
  ⟨313, .webSearch, 1427134203820419, 1, 173, 160⟩,
  ⟨392, .tag, 1794614400000000, 1, 173, 229⟩ ]

def claim : Claim := .both (Sets.searched 313) (Sets.tagged 313 .obj 392 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M052

#print axioms Cert.M052.verified
