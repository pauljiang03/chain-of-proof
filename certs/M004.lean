import ChainOfProof
open ChainOfProof

namespace Cert.M004

def cited : List Fact := [
  ⟨4, .usbInsert, 1427205513550110, 1, 2, 0⟩,
  ⟨375, .volumeOnDevice, 1794614400000000, 1, 2, 205⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩ ]

def claim : Claim := .both (Sets.deviceHolds 4 375) (Sets.tagged 4 .obj 315 194)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M004

#print axioms Cert.M004.verified
