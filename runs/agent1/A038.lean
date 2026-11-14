import ChainOfProof
open ChainOfProof

namespace Cert.A038

def cited : List Fact := [
  ⟨136, .webSearch, 1427134077288696, 1, 79, 70⟩ ]

def claim : Claim := Sets.searched 136

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A038

#print axioms Cert.A038.verified
