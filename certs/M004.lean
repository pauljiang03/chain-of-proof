import ChainOfProof
open ChainOfProof

namespace Cert.M004

def cited : List Fact := [
  ⟨4, .usbInsert, 1427205513550110, 1, 2, 0⟩,
  ⟨242, .volumeOnDevice, 1794614400000000, 1, 2, 121⟩,
  ⟨199, .tag, 1794614400000000, 1, 2, 116⟩ ]

def claim : Claim := .both (Sets.deviceHolds 4 242) (Sets.tagged 4 .obj 199 116)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M004

#print axioms Cert.M004.verified
