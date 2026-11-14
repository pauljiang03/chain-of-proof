import ChainOfProof
open ChainOfProof

namespace Cert.M001

def cited : List Fact := [
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨198, .tag, 1794614400000000, 1, 1, 115⟩ ]

def claim : Claim := .both (Sets.deviceHolds 1 241) (Sets.tagged 1 .obj 198 115)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M001

#print axioms Cert.M001.verified
