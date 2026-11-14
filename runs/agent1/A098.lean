import ChainOfProof
open ChainOfProof

namespace Cert.A098

def cited : List Fact := [
  ⟨196, .webSearch, 1427294814471205, 1, 113, 70⟩ ]

def claim : Claim := Sets.searched 196

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A098

#print axioms Cert.A098.verified
