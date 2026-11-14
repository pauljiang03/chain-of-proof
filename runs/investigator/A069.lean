import ChainOfProof
open ChainOfProof

namespace Cert.A069

def cited : List Fact := [
  ⟨268, .webSearch, 1427144026658464, 1, 158, 126⟩ ]

def claim : Claim := Sets.searched 268

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A069

#print axioms Cert.A069.verified
