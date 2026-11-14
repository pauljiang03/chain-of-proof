import ChainOfProof
open ChainOfProof

namespace Cert.A060

def cited : List Fact := [
  ⟨160, .fileModified, 1418746226000000, 2000000, 93, 69⟩,
  ⟨340, .tag, 1794614400000000, 1, 93, 198⟩ ]

def claim : Claim := Sets.tagged 160 .obj 340 198

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A060

#print axioms Cert.A060.verified
