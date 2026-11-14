import ChainOfProof
open ChainOfProof

namespace Cert.A014

def cited : List Fact := [
  ⟨213, .webSearch, 1427038096952833, 1, 127, 125⟩ ]

def claim : Claim := Sets.searched 213

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A014

#print axioms Cert.A014.verified
