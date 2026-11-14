import ChainOfProof
open ChainOfProof

namespace Cert.M060

def cited : List Fact := [
  ⟨323, .webSearch, 1427134615783075, 1, 182, 159⟩,
  ⟨477, .tag, 1794614400000000, 1, 182, 229⟩ ]

def claim : Claim := .both (Sets.searched 323) (Sets.tagged 323 .obj 477 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M060

#print axioms Cert.M060.verified
