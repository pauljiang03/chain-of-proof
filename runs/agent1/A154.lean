import ChainOfProof
open ChainOfProof

namespace Cert.A154

def cited : List Fact := [
  ⟨132, .webSearch, 1427133987545120, 1, 78, 69⟩,
  ⟨228, .tag, 1794614400000000, 1, 78, 117⟩ ]

def claim : Claim := Sets.tagged 132 .obj 228 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A154

#print axioms Cert.A154.verified
