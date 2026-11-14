import ChainOfProof
open ChainOfProof

namespace Cert.A054

def cited : List Fact := [
  ⟨152, .webSearch, 1427134544517540, 1, 91, 69⟩ ]

def claim : Claim := Sets.searched 152

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A054

#print axioms Cert.A054.verified
