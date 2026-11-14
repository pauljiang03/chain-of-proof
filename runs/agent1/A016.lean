import ChainOfProof
open ChainOfProof

namespace Cert.A016

def cited : List Fact := [
  ⟨114, .webSearch, 1427037861900251, 1, 68, 70⟩ ]

def claim : Claim := Sets.searched 114

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A016

#print axioms Cert.A016.verified
