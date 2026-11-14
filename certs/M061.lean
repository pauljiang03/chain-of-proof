import ChainOfProof
open ChainOfProof

namespace Cert.M061

def cited : List Fact := [
  ⟨324, .webSearch, 1427134634631105, 1, 183, 159⟩,
  ⟨465, .tag, 1794614400000000, 1, 183, 229⟩ ]

def claim : Claim := .both (Sets.searched 324) (Sets.tagged 324 .obj 465 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M061

#print axioms Cert.M061.verified
