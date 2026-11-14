import ChainOfProof
open ChainOfProof

namespace Cert.A030

def cited : List Fact := [
  ⟨229, .webSearch, 1427134072314186, 1, 135, 126⟩ ]

def claim : Claim := Sets.searched 229

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A030

#print axioms Cert.A030.verified
