import ChainOfProof
open ChainOfProof

namespace Cert.A010

def cited : List Fact := [
  ⟨209, .webSearch, 1427037052000000, 1, 124, 125⟩ ]

def claim : Claim := Sets.searched 209

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A010

#print axioms Cert.A010.verified
