import ChainOfProof
open ChainOfProof

namespace Cert.A165

def cited : List Fact := [
  ⟨153, .webSearch, 1427134615783075, 1, 92, 69⟩,
  ⟨227, .tag, 1794614400000000, 1, 92, 117⟩ ]

def claim : Claim := Sets.tagged 153 .obj 227 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A165

#print axioms Cert.A165.verified
