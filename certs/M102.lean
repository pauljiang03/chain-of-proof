import ChainOfProof
open ChainOfProof

namespace Cert.M102

def cited : List Fact := [
  ⟨88, .fileCreated, 1427144120150000, 10000, 72, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨189, .fileModified, 1367953792000000, 2000000, 72, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 88 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 88 189)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M102

#print axioms Cert.M102.verified
