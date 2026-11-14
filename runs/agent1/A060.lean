import ChainOfProof
open ChainOfProof

namespace Cert.A060

def cited : List Fact := [
  ⟨158, .webSearch, 1427134723263901, 1, 95, 69⟩ ]

def claim : Claim := Sets.searched 158

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A060

#print axioms Cert.A060.verified
