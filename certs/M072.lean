import ChainOfProof
open ChainOfProof

namespace Cert.M072

def cited : List Fact := [
  ⟨365, .webSearch, 1427294804771004, 1, 202, 160⟩,
  ⟨464, .tag, 1794614400000000, 1, 202, 229⟩ ]

def claim : Claim := .both (Sets.searched 365) (Sets.tagged 365 .obj 464 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M072

#print axioms Cert.M072.verified
