import ChainOfProof
open ChainOfProof

namespace Cert.M133

def cited : List Fact := [
  ⟨119, .fileCreated, 1427205612590000, 10000, 103, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨167, .fileModified, 1420491668000000, 2000000, 103, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 119 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 119) (Sets.copiedHere 119 167))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M133

#print axioms Cert.M133.verified
