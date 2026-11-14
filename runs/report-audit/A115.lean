import ChainOfProof
open ChainOfProof

namespace Cert.A115

def cited : List Fact := [
  ⟨290, .webSearch, 1427294804752905, 1, 168, 126⟩ ]

def claim : Claim := Sets.searched 290

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A115

#print axioms Cert.A115.verified
