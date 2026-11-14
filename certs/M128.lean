import ChainOfProof
open ChainOfProof

namespace Cert.M128

def cited : List Fact := [
  ⟨114, .fileCreated, 1427205583520000, 10000, 98, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨241, .fileModified, 1421766824000000, 2000000, 98, 69⟩,
  ⟨419, .tag, 1794614400000000, 1, 98, 240⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 114 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 114) (.both (Sets.copiedHere 114 241) (Sets.tagged 114 .obj 419 240)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M128

#print axioms Cert.M128.verified
