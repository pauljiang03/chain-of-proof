import ChainOfProof
open ChainOfProof

namespace Cert.A056

def cited : List Fact := [
  ⟨154, .webSearch, 1427134634631105, 1, 93, 69⟩ ]

def claim : Claim := Sets.searched 154

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A056

#print axioms Cert.A056.verified
