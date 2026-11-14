import ChainOfProof
open ChainOfProof

namespace Cert.A056

def cited : List Fact := [
  ⟨255, .webSearch, 1427134726050680, 1, 151, 125⟩ ]

def claim : Claim := Sets.searched 255

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A056

#print axioms Cert.A056.verified
