import ChainOfProof
open ChainOfProof

namespace Cert.M067

def cited : List Fact := [
  ⟨160, .webSearch, 1427134743860449, 1, 96, 69⟩,
  ⟨222, .tag, 1794614400000000, 1, 96, 117⟩ ]

def claim : Claim := .both (Sets.searched 160) (Sets.tagged 160 .obj 222 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M067

#print axioms Cert.M067.verified
