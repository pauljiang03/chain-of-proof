import ChainOfProof
open ChainOfProof

namespace Cert.A061

def cited : List Fact := [
  ⟨260, .webSearch, 1427140564087328, 1, 155, 125⟩ ]

def claim : Claim := Sets.searched 260

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A061

#print axioms Cert.A061.verified
