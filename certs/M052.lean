import ChainOfProof
open ChainOfProof

namespace Cert.M052

def cited : List Fact := [
  ⟨143, .webSearch, 1427134203820419, 1, 83, 70⟩,
  ⟨201, .tag, 1794614400000000, 1, 83, 117⟩ ]

def claim : Claim := .both (Sets.searched 143) (Sets.tagged 143 .obj 201 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M052

#print axioms Cert.M052.verified
