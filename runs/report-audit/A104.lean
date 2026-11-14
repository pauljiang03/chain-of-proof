import ChainOfProof
open ChainOfProof

namespace Cert.A104

def cited : List Fact := [
  ⟨243, .webSearch, 1427134400892344, 1, 143, 126⟩ ]

def claim : Claim := Sets.searched 243

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A104

#print axioms Cert.A104.verified
