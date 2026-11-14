import ChainOfProof
open ChainOfProof

namespace Cert.M129

def cited : List Fact := [
  ⟨115, .fileCreated, 1427205583550000, 10000, 99, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨165, .fileModified, 1420473442000000, 2000000, 99, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 115 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 115) (Sets.copiedHere 115 165))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M129

#print axioms Cert.M129.verified
