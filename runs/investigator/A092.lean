import ChainOfProof
open ChainOfProof

namespace Cert.A092

def cited : List Fact := [
  ⟨291, .webSearch, 1427294804771004, 1, 168, 126⟩ ]

def claim : Claim := Sets.searched 291

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A092

#print axioms Cert.A092.verified
