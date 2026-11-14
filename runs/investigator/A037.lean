import ChainOfProof
open ChainOfProof

namespace Cert.A037

def cited : List Fact := [
  ⟨236, .webSearch, 1427134111817280, 1, 137, 126⟩ ]

def claim : Claim := Sets.searched 236

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A037

#print axioms Cert.A037.verified
