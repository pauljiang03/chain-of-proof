import ChainOfProof
open ChainOfProof

namespace Cert.A151

def cited : List Fact := [
  ⟨122, .webSearch, 1427133764343210, 1, 75, 69⟩,
  ⟨233, .tag, 1794614400000000, 1, 75, 117⟩ ]

def claim : Claim := Sets.tagged 122 .obj 233 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A151

#print axioms Cert.A151.verified
