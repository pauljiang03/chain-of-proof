import ChainOfProof
open ChainOfProof

namespace Cert.M052

def cited : List Fact := [
  ⟨239, .webSearch, 1427134203820419, 1, 139, 126⟩,
  ⟨318, .tag, 1794614400000000, 1, 139, 195⟩ ]

def claim : Claim := .both (Sets.searched 239) (Sets.tagged 239 .obj 318 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M052

#print axioms Cert.M052.verified
