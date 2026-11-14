import ChainOfProof
open ChainOfProof

namespace Cert.A052

def cited : List Fact := [
  ⟨150, .webSearch, 1427134451977428, 1, 89, 70⟩ ]

def claim : Claim := Sets.searched 150

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A052

#print axioms Cert.A052.verified
