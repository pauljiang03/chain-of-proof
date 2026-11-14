import ChainOfProof
open ChainOfProof

namespace Cert.A087

def cited : List Fact := [
  ⟨286, .webSearch, 1427144158742157, 1, 166, 126⟩ ]

def claim : Claim := Sets.searched 286

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A087

#print axioms Cert.A087.verified
