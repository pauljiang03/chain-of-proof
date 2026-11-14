import ChainOfProof
open ChainOfProof

namespace Cert.A012

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨199, .tag, 1794614400000000, 1, 2, 116⟩ ]

def claim : Claim := Sets.tagged 3 .obj 199 116

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A012

#print axioms Cert.A012.verified
