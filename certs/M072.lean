import ChainOfProof
open ChainOfProof

namespace Cert.M072

def cited : List Fact := [
  ⟨195, .webSearch, 1427294804771004, 1, 112, 70⟩,
  ⟨215, .tag, 1794614400000000, 1, 112, 117⟩ ]

def claim : Claim := .both (Sets.searched 195) (Sets.tagged 195 .obj 215 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M072

#print axioms Cert.M072.verified
