import ChainOfProof
open ChainOfProof

namespace Cert.M339

def cited : List Fact := [
  ⟨12688, .fileContent, 1794614400000000, 1, 53, 16124⟩,
  ⟨12722, .fileContent, 1794614400000000, 1, 101, 16124⟩,
  ⟨12771, .fileContent, 1794614400000000, 1, 128, 16124⟩,
  ⟨12773, .fileContent, 1794614400000000, 1, 129, 16124⟩ ]

def claim : Claim := .both (Sets.sameContent 12688 12722) (.both (Sets.sameContent 12722 12771) (Sets.sameContent 12771 12773))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M339

#print axioms Cert.M339.verified
