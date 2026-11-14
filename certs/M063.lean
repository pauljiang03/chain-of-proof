import ChainOfProof
open ChainOfProof

namespace Cert.M063

def cited : List Fact := [
  ⟨326, .webSearch, 1427134695855272, 1, 184, 159⟩,
  ⟨484, .tag, 1794614400000000, 1, 184, 229⟩ ]

def claim : Claim := .both (Sets.searched 326) (Sets.tagged 326 .obj 484 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M063

#print axioms Cert.M063.verified
