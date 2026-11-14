import ChainOfProof
open ChainOfProof

namespace Cert.A068

def cited : List Fact := [
  ⟨267, .webSearch, 1427144026618464, 1, 158, 126⟩ ]

def claim : Claim := Sets.searched 267

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A068

#print axioms Cert.A068.verified
