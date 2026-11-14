import ChainOfProof
open ChainOfProof

namespace Cert.M010

def cited : List Fact := [
  ⟨27, .lnkTarget, 1427135901214563, 1, 23, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨198, .tag, 1794614400000000, 1, 1, 115⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 27 241) (.both (Sets.deviceHolds 1 241) (Sets.tagged 1 .obj 198 115))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M010

#print axioms Cert.M010.verified
