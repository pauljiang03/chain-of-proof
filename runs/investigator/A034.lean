import ChainOfProof
open ChainOfProof

namespace Cert.A034

def cited : List Fact := [
  ⟨233, .webSearch, 1427134078080700, 1, 136, 126⟩ ]

def claim : Claim := Sets.searched 233

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A034

#print axioms Cert.A034.verified
