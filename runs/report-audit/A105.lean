import ChainOfProof
open ChainOfProof

namespace Cert.A105

def cited : List Fact := [
  ⟨244, .webSearch, 1427134417494371, 1, 144, 126⟩ ]

def claim : Claim := Sets.searched 244

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A105

#print axioms Cert.A105.verified
