import ChainOfProof
open ChainOfProof

namespace Cert.A087

def cited : List Fact := [
  ⟨185, .webSearch, 1427144156134653, 1, 108, 70⟩ ]

def claim : Claim := Sets.searched 185

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A087

#print axioms Cert.A087.verified
