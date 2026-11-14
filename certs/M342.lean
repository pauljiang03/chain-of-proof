import ChainOfProof
open ChainOfProof

namespace Cert.M342

def cited : List Fact := [
  ⟨12692, .fileContent, 1794614400000000, 1, 46, 16128⟩,
  ⟨12695, .fileContent, 1794614400000000, 1, 47, 16128⟩ ]

def claim : Claim := Sets.sameContent 12692 12695

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M342

#print axioms Cert.M342.verified
