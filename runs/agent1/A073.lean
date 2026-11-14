import ChainOfProof
open ChainOfProof

namespace Cert.A073

def cited : List Fact := [
  ⟨171, .webSearch, 1427144026618464, 1, 102, 70⟩ ]

def claim : Claim := Sets.searched 171

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A073

#print axioms Cert.A073.verified
