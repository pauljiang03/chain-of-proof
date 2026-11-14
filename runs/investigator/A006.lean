import ChainOfProof
open ChainOfProof

namespace Cert.A006

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩ ]

def claim : Claim := Sets.tagged 3 .obj 315 194

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A006

#print axioms Cert.A006.verified
