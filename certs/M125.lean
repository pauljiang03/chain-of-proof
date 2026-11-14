import ChainOfProof
open ChainOfProof

namespace Cert.M125

def cited : List Fact := [
  ⟨111, .fileCreated, 1427205579680000, 10000, 95, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨226, .fileModified, 1420751304000000, 2000000, 95, 69⟩,
  ⟨416, .tag, 1794614400000000, 1, 95, 237⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 111 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 111) (.both (Sets.copiedHere 111 226) (Sets.tagged 111 .obj 416 237)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M125

#print axioms Cert.M125.verified
