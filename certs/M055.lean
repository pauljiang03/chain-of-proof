import ChainOfProof
open ChainOfProof

namespace Cert.M055

def cited : List Fact := [
  ⟨147, .webSearch, 1427134400892344, 1, 87, 70⟩,
  ⟨218, .tag, 1794614400000000, 1, 87, 117⟩ ]

def claim : Claim := .both (Sets.searched 147) (Sets.tagged 147 .obj 218 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M055

#print axioms Cert.M055.verified
