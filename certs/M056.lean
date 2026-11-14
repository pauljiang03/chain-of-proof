import ChainOfProof
open ChainOfProof

namespace Cert.M056

def cited : List Fact := [
  ⟨148, .webSearch, 1427134417494371, 1, 88, 70⟩,
  ⟨219, .tag, 1794614400000000, 1, 88, 117⟩ ]

def claim : Claim := .both (Sets.searched 148) (Sets.tagged 148 .obj 219 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M056

#print axioms Cert.M056.verified
