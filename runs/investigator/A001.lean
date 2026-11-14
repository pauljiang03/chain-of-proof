import ChainOfProof
open ChainOfProof

namespace Cert.A001

def cited : List Fact := [
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.deviceHolds 1 374

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A001

#print axioms Cert.A001.verified
