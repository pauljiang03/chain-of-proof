import ChainOfProof
open ChainOfProof

namespace Cert.A034

def cited : List Fact := [
  ⟨132, .webSearch, 1427133987545120, 1, 78, 69⟩ ]

def claim : Claim := Sets.searched 132

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A034

#print axioms Cert.A034.verified
