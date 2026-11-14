import ChainOfProof
open ChainOfProof

namespace Cert.M067

def cited : List Fact := [
  ⟨256, .webSearch, 1427134743860449, 1, 152, 125⟩,
  ⟨350, .tag, 1794614400000000, 1, 152, 195⟩ ]

def claim : Claim := .both (Sets.searched 256) (Sets.tagged 256 .obj 350 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M067

#print axioms Cert.M067.verified
