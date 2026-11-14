import ChainOfProof
open ChainOfProof

namespace Cert.M048

def cited : List Fact := [
  ⟨228, .webSearch, 1427133987545120, 1, 134, 125⟩,
  ⟨356, .tag, 1794614400000000, 1, 134, 195⟩ ]

def claim : Claim := .both (Sets.searched 228) (Sets.tagged 228 .obj 356 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M048

#print axioms Cert.M048.verified
