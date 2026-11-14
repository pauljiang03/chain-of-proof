import ChainOfProof
open ChainOfProof

namespace Cert.M347

def cited : List Fact := [
  ⟨12715, .fileContent, 1794614400000000, 1, 94, 16140⟩,
  ⟨12757, .fileContent, 1794614400000000, 1, 114, 16140⟩,
  ⟨12761, .fileContent, 1794614400000000, 1, 115, 16140⟩ ]

def claim : Claim := .both (Sets.sameContent 12715 12757) (Sets.sameContent 12757 12761)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M347

#print axioms Cert.M347.verified
