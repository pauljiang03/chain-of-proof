import ChainOfProof
open ChainOfProof

namespace Cert.A088

def cited : List Fact := [
  ⟨186, .webSearch, 1427144156154654, 1, 108, 70⟩ ]

def claim : Claim := Sets.searched 186

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A088

#print axioms Cert.A088.verified
