import ChainOfProof
open ChainOfProof

namespace Cert.M062

def cited : List Fact := [
  ⟨325, .webSearch, 1427134690237438, 1, 184, 159⟩,
  ⟨484, .tag, 1794614400000000, 1, 184, 229⟩ ]

def claim : Claim := .both (Sets.searched 325) (Sets.tagged 325 .obj 484 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M062

#print axioms Cert.M062.verified
