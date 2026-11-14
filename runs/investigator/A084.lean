import ChainOfProof
open ChainOfProof

namespace Cert.A084

def cited : List Fact := [
  ⟨283, .webSearch, 1427144157412157, 1, 165, 126⟩ ]

def claim : Claim := Sets.searched 283

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A084

#print axioms Cert.A084.verified
