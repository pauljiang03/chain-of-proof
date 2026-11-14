import ChainOfProof
open ChainOfProof

namespace Cert.M050

def cited : List Fact := [
  ⟨141, .webSearch, 1427134134101318, 1, 82, 70⟩,
  ⟨224, .tag, 1794614400000000, 1, 82, 117⟩ ]

def claim : Claim := .both (Sets.searched 141) (Sets.tagged 141 .obj 224 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M050

#print axioms Cert.M050.verified
