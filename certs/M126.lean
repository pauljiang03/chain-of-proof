import ChainOfProof
open ChainOfProof

namespace Cert.M126

def cited : List Fact := [
  ⟨112, .fileCreated, 1427205579710000, 10000, 96, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨198, .fileModified, 1417459826000000, 2000000, 96, 69⟩,
  ⟨417, .tag, 1794614400000000, 1, 96, 238⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 112 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 112) (.both (Sets.copiedHere 112 198) (Sets.tagged 112 .obj 417 238)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M126

#print axioms Cert.M126.verified
