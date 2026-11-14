import ChainOfProof
open ChainOfProof

namespace Cert.A029

def cited : List Fact := [
  ⟨228, .webSearch, 1427133987545120, 1, 134, 125⟩ ]

def claim : Claim := Sets.searched 228

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A029

#print axioms Cert.A029.verified
