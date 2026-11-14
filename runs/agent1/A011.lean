import ChainOfProof
open ChainOfProof

namespace Cert.A011

def cited : List Fact := [
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨198, .tag, 1794614400000000, 1, 1, 115⟩ ]

def claim : Claim := Sets.tagged 1 .obj 198 115

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A011

#print axioms Cert.A011.verified
