import ChainOfProof
open ChainOfProof

namespace Cert.A088

def cited : List Fact := [
  ⟨287, .webSearch, 1427144168707174, 1, 158, 126⟩ ]

def claim : Claim := Sets.searched 287

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A088

#print axioms Cert.A088.verified
