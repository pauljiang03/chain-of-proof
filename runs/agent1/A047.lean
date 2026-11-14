import ChainOfProof
open ChainOfProof

namespace Cert.A047

def cited : List Fact := [
  ⟨145, .webSearch, 1427134310582693, 1, 85, 70⟩ ]

def claim : Claim := Sets.searched 145

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A047

#print axioms Cert.A047.verified
