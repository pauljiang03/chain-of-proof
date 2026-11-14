import ChainOfProof
open ChainOfProof

namespace Cert.M043

def cited : List Fact := [
  ⟨297, .webSearch, 1427133915865196, 1, 166, 159⟩,
  ⟨480, .tag, 1794614400000000, 1, 166, 229⟩ ]

def claim : Claim := .both (Sets.searched 297) (Sets.tagged 297 .obj 480 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M043

#print axioms Cert.M043.verified
