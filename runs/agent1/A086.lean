import ChainOfProof
open ChainOfProof

namespace Cert.A086

def cited : List Fact := [
  ⟨184, .webSearch, 1427144154827650, 1, 107, 70⟩ ]

def claim : Claim := Sets.searched 184

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A086

#print axioms Cert.A086.verified
