import ChainOfProof
open ChainOfProof

namespace Cert.M002

def cited : List Fact := [
  ⟨2, .usbInsert, 1427204280014221, 1, 1, 0⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨198, .tag, 1794614400000000, 1, 1, 115⟩ ]

def claim : Claim := .both (Sets.deviceHolds 2 241) (Sets.tagged 2 .obj 198 115)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M002

#print axioms Cert.M002.verified
