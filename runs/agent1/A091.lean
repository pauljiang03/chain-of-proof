import ChainOfProof
open ChainOfProof

namespace Cert.A091

def cited : List Fact := [
  ⟨189, .webSearch, 1427144158732159, 1, 110, 70⟩ ]

def claim : Claim := Sets.searched 189

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A091

#print axioms Cert.A091.verified
