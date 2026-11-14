import ChainOfProof
open ChainOfProof

namespace Cert.A072

def cited : List Fact := [
  ⟨271, .webSearch, 1427144110333084, 1, 160, 126⟩ ]

def claim : Claim := Sets.searched 271

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A072

#print axioms Cert.A072.verified
