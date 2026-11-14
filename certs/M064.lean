import ChainOfProof
open ChainOfProof

namespace Cert.M064

def cited : List Fact := [
  ⟨327, .webSearch, 1427134710872763, 1, 185, 159⟩,
  ⟨479, .tag, 1794614400000000, 1, 185, 229⟩ ]

def claim : Claim := .both (Sets.searched 327) (Sets.tagged 327 .obj 479 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M064

#print axioms Cert.M064.verified
