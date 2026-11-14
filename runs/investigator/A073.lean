import ChainOfProof
open ChainOfProof

namespace Cert.A073

def cited : List Fact := [
  ⟨272, .webSearch, 1427144110353085, 1, 160, 126⟩ ]

def claim : Claim := Sets.searched 272

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A073

#print axioms Cert.A073.verified
