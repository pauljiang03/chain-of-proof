import ChainOfProof
open ChainOfProof

namespace Cert.M003

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨497, .volumeOnDevice, 1794614400000000, 1, 2, 253⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩ ]

def claim : Claim := .both (Sets.deviceHolds 3 497) (Sets.tagged 3 .obj 389 228)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M003

#print axioms Cert.M003.verified
