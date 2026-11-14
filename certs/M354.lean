import ChainOfProof
open ChainOfProof

namespace Cert.M354

def cited : List Fact := [
  ⟨12724, .fileContent, 1794614400000000, 1, 103, 16147⟩,
  ⟨12775, .fileContent, 1794614400000000, 1, 132, 16147⟩,
  ⟨12781, .fileContent, 1794614400000000, 1, 134, 16147⟩ ]

def claim : Claim := .both (Sets.sameContent 12724 12775) (Sets.sameContent 12775 12781)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M354

#print axioms Cert.M354.verified
