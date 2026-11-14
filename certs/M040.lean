import ChainOfProof
open ChainOfProof

namespace Cert.M040

def cited : List Fact := [
  ⟨124, .webSearch, 1427133811261408, 1, 75, 69⟩,
  ⟨233, .tag, 1794614400000000, 1, 75, 117⟩ ]

def claim : Claim := .both (Sets.searched 124) (Sets.tagged 124 .obj 233 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M040

#print axioms Cert.M040.verified
