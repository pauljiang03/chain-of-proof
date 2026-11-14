import ChainOfProof
open ChainOfProof

namespace Cert.M356

def cited : List Fact := [
  ⟨12726, .fileContent, 1794614400000000, 1, 105, 16149⟩,
  ⟨12777, .fileContent, 1794614400000000, 1, 136, 16149⟩,
  ⟨12783, .fileContent, 1794614400000000, 1, 137, 16149⟩ ]

def claim : Claim := .both (Sets.sameContent 12726 12777) (Sets.sameContent 12777 12783)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M356

#print axioms Cert.M356.verified
