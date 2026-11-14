import ChainOfProof
open ChainOfProof

namespace Cert.A178

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.deviceExamined 3 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A178

#print axioms Cert.A178.verified
