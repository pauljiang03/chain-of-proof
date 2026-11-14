import ChainOfProof
open ChainOfProof

namespace Cert.A059

def cited : List Fact := [
  ⟨258, .webSearch, 1427140099531147, 1, 153, 125⟩ ]

def claim : Claim := Sets.searched 258

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A059

#print axioms Cert.A059.verified
