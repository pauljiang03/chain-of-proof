import ChainOfProof
open ChainOfProof

namespace Cert.A019

def cited : List Fact := [
  ⟨117, .webSearch, 1427038096952833, 1, 71, 69⟩ ]

def claim : Claim := Sets.searched 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A019

#print axioms Cert.A019.verified
