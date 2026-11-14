import ChainOfProof
open ChainOfProof

namespace Cert.A005

def cited : List Fact := [
  ⟨217, .webSearch, 1427133729303892, 1, 130, 125⟩ ]

def claim : Claim := Sets.searched 217

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A005

#print axioms Cert.A005.verified
