import ChainOfProof
open ChainOfProof

namespace Cert.A079

def cited : List Fact := [
  ⟨177, .webSearch, 1427144117465595, 1, 105, 70⟩ ]

def claim : Claim := Sets.searched 177

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A079

#print axioms Cert.A079.verified
