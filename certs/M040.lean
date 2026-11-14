import ChainOfProof
open ChainOfProof

namespace Cert.M040

def cited : List Fact := [
  ⟨294, .webSearch, 1427133811261408, 1, 165, 159⟩,
  ⟨483, .tag, 1794614400000000, 1, 165, 229⟩ ]

def claim : Claim := .both (Sets.searched 294) (Sets.tagged 294 .obj 483 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M040

#print axioms Cert.M040.verified
