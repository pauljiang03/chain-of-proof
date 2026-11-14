import ChainOfProof
open ChainOfProof

namespace Cert.A003

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨375, .volumeOnDevice, 1794614400000000, 1, 2, 205⟩ ]

def claim : Claim := Sets.deviceHolds 3 375

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A003

#print axioms Cert.A003.verified
