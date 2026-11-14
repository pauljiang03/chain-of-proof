import ChainOfProof
open ChainOfProof

namespace Cert.M067

def cited : List Fact := [
  ⟨330, .webSearch, 1427134743860449, 1, 186, 159⟩,
  ⟨471, .tag, 1794614400000000, 1, 186, 229⟩ ]

def claim : Claim := .both (Sets.searched 330) (Sets.tagged 330 .obj 471 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M067

#print axioms Cert.M067.verified
