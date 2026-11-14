import ChainOfProof
open ChainOfProof

namespace Cert.M129

def cited : List Fact := [
  ⟨115, .fileCreated, 1427205583550000, 10000, 99, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨217, .fileModified, 1420473442000000, 2000000, 99, 69⟩,
  ⟨420, .tag, 1794614400000000, 1, 99, 241⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 115 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 115) (.both (Sets.copiedHere 115 217) (Sets.tagged 115 .obj 420 241)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M129

#print axioms Cert.M129.verified
