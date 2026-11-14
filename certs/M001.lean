import ChainOfProof
open ChainOfProof

namespace Cert.M001

def cited : List Fact := [
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨496, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨388, .tag, 1794614400000000, 1, 1, 227⟩ ]

def claim : Claim := .both (Sets.deviceHolds 1 496) (Sets.tagged 1 .obj 388 227)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M001

#print axioms Cert.M001.verified
