import ChainOfProof
open ChainOfProof

namespace Cert.M040

def cited : List Fact := [
  ⟨220, .webSearch, 1427133811261408, 1, 131, 125⟩,
  ⟨361, .tag, 1794614400000000, 1, 131, 195⟩ ]

def claim : Claim := .both (Sets.searched 220) (Sets.tagged 220 .obj 361 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M040

#print axioms Cert.M040.verified
