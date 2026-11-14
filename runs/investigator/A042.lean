import ChainOfProof
open ChainOfProof

namespace Cert.A042

def cited : List Fact := [
  ⟨241, .webSearch, 1427134310582693, 1, 141, 126⟩ ]

def claim : Claim := Sets.searched 241

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A042

#print axioms Cert.A042.verified
