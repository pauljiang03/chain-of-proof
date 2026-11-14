import ChainOfProof
open ChainOfProof

namespace Cert.A036

def cited : List Fact := [
  ⟨134, .webSearch, 1427134074981194, 1, 79, 70⟩ ]

def claim : Claim := Sets.searched 134

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A036

#print axioms Cert.A036.verified
