import ChainOfProof
open ChainOfProof

namespace Cert.A050

def cited : List Fact := [
  ⟨249, .webSearch, 1427134615783075, 1, 148, 125⟩ ]

def claim : Claim := Sets.searched 249

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A050

#print axioms Cert.A050.verified
