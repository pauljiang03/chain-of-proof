import ChainOfProof
open ChainOfProof

namespace Cert.M109

def cited : List Fact := [
  ⟨95, .fileCreated, 1427144130110000, 10000, 79, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨190, .fileModified, 1367953820000000, 2000000, 79, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 95 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 95 190)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M109

#print axioms Cert.M109.verified
