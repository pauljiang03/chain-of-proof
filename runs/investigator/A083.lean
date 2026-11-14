import ChainOfProof
open ChainOfProof

namespace Cert.A083

def cited : List Fact := [
  ⟨282, .webSearch, 1427144156154654, 1, 164, 126⟩ ]

def claim : Claim := Sets.searched 282

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A083

#print axioms Cert.A083.verified
