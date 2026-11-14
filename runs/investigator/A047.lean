import ChainOfProof
open ChainOfProof

namespace Cert.A047

def cited : List Fact := [
  ⟨246, .webSearch, 1427134451977428, 1, 145, 126⟩ ]

def claim : Claim := Sets.searched 246

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A047

#print axioms Cert.A047.verified
