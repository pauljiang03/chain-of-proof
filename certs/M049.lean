import ChainOfProof
open ChainOfProof

namespace Cert.M049

def cited : List Fact := [
  ⟨140, .webSearch, 1427134111817280, 1, 81, 70⟩,
  ⟨200, .tag, 1794614400000000, 1, 81, 117⟩ ]

def claim : Claim := .both (Sets.searched 140) (Sets.tagged 140 .obj 200 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M049

#print axioms Cert.M049.verified
