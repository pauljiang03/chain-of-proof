import ChainOfProof
open ChainOfProof

namespace Cert.A080

def cited : List Fact := [
  ⟨279, .webSearch, 1427144154787651, 1, 163, 126⟩ ]

def claim : Claim := Sets.searched 279

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A080

#print axioms Cert.A080.verified
