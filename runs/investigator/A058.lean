import ChainOfProof
open ChainOfProof

namespace Cert.A058

def cited : List Fact := [
  ⟨257, .webSearch, 1427140063009623, 1, 152, 125⟩ ]

def claim : Claim := Sets.searched 257

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A058

#print axioms Cert.A058.verified
