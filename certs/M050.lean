import ChainOfProof
open ChainOfProof

namespace Cert.M050

def cited : List Fact := [
  ⟨311, .webSearch, 1427134134101318, 1, 172, 160⟩,
  ⟨474, .tag, 1794614400000000, 1, 172, 229⟩ ]

def claim : Claim := .both (Sets.searched 311) (Sets.tagged 311 .obj 474 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M050

#print axioms Cert.M050.verified
