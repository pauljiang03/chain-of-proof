import ChainOfProof
open ChainOfProof

namespace Cert.A065

def cited : List Fact := [
  ⟨264, .webSearch, 1427143522377234, 1, 156, 126⟩ ]

def claim : Claim := Sets.searched 264

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A065

#print axioms Cert.A065.verified
