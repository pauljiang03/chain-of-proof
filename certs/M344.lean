import ChainOfProof
open ChainOfProof

namespace Cert.M344

def cited : List Fact := [
  ⟨12698, .fileContent, 1794614400000000, 1, 60, 16131⟩,
  ⟨12704, .fileContent, 1794614400000000, 1, 54, 16131⟩,
  ⟨12709, .fileContent, 1794614400000000, 1, 63, 16131⟩ ]

def claim : Claim := .both (Sets.sameContent 12698 12704) (Sets.sameContent 12704 12709)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M344

#print axioms Cert.M344.verified
