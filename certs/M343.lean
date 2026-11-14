import ChainOfProof
open ChainOfProof

namespace Cert.M343

def cited : List Fact := [
  ⟨12693, .fileContent, 1794614400000000, 1, 49, 16129⟩,
  ⟨12696, .fileContent, 1794614400000000, 1, 50, 16129⟩ ]

def claim : Claim := Sets.sameContent 12693 12696

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M343

#print axioms Cert.M343.verified
