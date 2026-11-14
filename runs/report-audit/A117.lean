import ChainOfProof
open ChainOfProof

namespace Cert.A117

def cited : List Fact := [
  ⟨293, .webSearch, 1427294871248203, 1, 170, 126⟩ ]

def claim : Claim := Sets.searched 293

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A117

#print axioms Cert.A117.verified
