import ChainOfProof
open ChainOfProof

namespace Cert.A011

def cited : List Fact := [
  ⟨210, .webSearch, 1427037861900251, 1, 124, 126⟩ ]

def claim : Claim := Sets.searched 210

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A011

#print axioms Cert.A011.verified
