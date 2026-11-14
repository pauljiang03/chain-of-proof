import ChainOfProof
open ChainOfProof

namespace Cert.A038

def cited : List Fact := [
  ⟨237, .webSearch, 1427134134101318, 1, 138, 126⟩ ]

def claim : Claim := Sets.searched 237

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A038

#print axioms Cert.A038.verified
