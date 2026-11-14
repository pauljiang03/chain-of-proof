import ChainOfProof
open ChainOfProof

namespace Cert.M352

def cited : List Fact := [
  ⟨12720, .fileContent, 1794614400000000, 1, 99, 16145⟩,
  ⟨12766, .fileContent, 1794614400000000, 1, 124, 16145⟩,
  ⟨12769, .fileContent, 1794614400000000, 1, 125, 16145⟩ ]

def claim : Claim := .both (Sets.sameContent 12720 12766) (Sets.sameContent 12766 12769)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M352

#print axioms Cert.M352.verified
