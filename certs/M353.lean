import ChainOfProof
open ChainOfProof

namespace Cert.M353

def cited : List Fact := [
  ⟨12721, .fileContent, 1794614400000000, 1, 100, 16146⟩,
  ⟨12767, .fileContent, 1794614400000000, 1, 126, 16146⟩,
  ⟨12770, .fileContent, 1794614400000000, 1, 127, 16146⟩ ]

def claim : Claim := .both (Sets.sameContent 12721 12767) (Sets.sameContent 12767 12770)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M353

#print axioms Cert.M353.verified
