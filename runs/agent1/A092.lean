import ChainOfProof
open ChainOfProof

namespace Cert.A092

def cited : List Fact := [
  ⟨190, .webSearch, 1427144158742157, 1, 110, 70⟩ ]

def claim : Claim := Sets.searched 190

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A092

#print axioms Cert.A092.verified
