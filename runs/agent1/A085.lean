import ChainOfProof
open ChainOfProof

namespace Cert.A085

def cited : List Fact := [
  ⟨183, .webSearch, 1427144154787651, 1, 107, 70⟩ ]

def claim : Claim := Sets.searched 183

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A085

#print axioms Cert.A085.verified
