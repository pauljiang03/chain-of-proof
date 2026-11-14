import ChainOfProof
open ChainOfProof

namespace Cert.M341

def cited : List Fact := [
  ⟨12691, .fileContent, 1794614400000000, 1, 58, 16127⟩,
  ⟨12694, .fileContent, 1794614400000000, 1, 59, 16127⟩ ]

def claim : Claim := Sets.sameContent 12691 12694

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M341

#print axioms Cert.M341.verified
