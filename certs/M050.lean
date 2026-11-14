import ChainOfProof
open ChainOfProof

namespace Cert.M050

def cited : List Fact := [
  ⟨237, .webSearch, 1427134134101318, 1, 138, 126⟩,
  ⟨352, .tag, 1794614400000000, 1, 138, 195⟩ ]

def claim : Claim := .both (Sets.searched 237) (Sets.tagged 237 .obj 352 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M050

#print axioms Cert.M050.verified
