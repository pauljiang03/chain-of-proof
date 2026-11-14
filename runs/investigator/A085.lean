import ChainOfProof
open ChainOfProof

namespace Cert.A085

def cited : List Fact := [
  ⟨284, .webSearch, 1427144157439657, 1, 165, 126⟩ ]

def claim : Claim := Sets.searched 284

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A085

#print axioms Cert.A085.verified
