import ChainOfProof
open ChainOfProof

namespace Cert.A061

def cited : List Fact := [
  ⟨159, .webSearch, 1427134726050680, 1, 95, 69⟩ ]

def claim : Claim := Sets.searched 159

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A061

#print axioms Cert.A061.verified
