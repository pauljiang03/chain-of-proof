import ChainOfProof
open ChainOfProof

namespace Cert.A110

def cited : List Fact := [
  ⟨228, .webSearch, 1427133987545120, 1, 134, 125⟩,
  ⟨356, .tag, 1794614400000000, 1, 134, 195⟩ ]

def claim : Claim := Sets.tagged 228 .obj 356 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A110

#print axioms Cert.A110.verified
