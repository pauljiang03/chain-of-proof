import ChainOfProof
open ChainOfProof

namespace Cert.M355

def cited : List Fact := [
  ⟨12725, .fileContent, 1794614400000000, 1, 104, 16148⟩,
  ⟨12776, .fileContent, 1794614400000000, 1, 133, 16148⟩,
  ⟨12782, .fileContent, 1794614400000000, 1, 135, 16148⟩ ]

def claim : Claim := .both (Sets.sameContent 12725 12776) (Sets.sameContent 12776 12782)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M355

#print axioms Cert.M355.verified
