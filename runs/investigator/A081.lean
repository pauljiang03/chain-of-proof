import ChainOfProof
open ChainOfProof

namespace Cert.A081

def cited : List Fact := [
  ⟨280, .webSearch, 1427144154827650, 1, 163, 126⟩ ]

def claim : Claim := Sets.searched 280

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A081

#print axioms Cert.A081.verified
