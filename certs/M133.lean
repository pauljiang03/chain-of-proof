import ChainOfProof
open ChainOfProof

namespace Cert.M133

def cited : List Fact := [
  ⟨119, .fileCreated, 1427205612590000, 10000, 103, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨223, .fileModified, 1420491668000000, 2000000, 103, 69⟩,
  ⟨424, .tag, 1794614400000000, 1, 103, 243⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 119 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 119) (.both (Sets.copiedHere 119 223) (Sets.tagged 119 .obj 424 243)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M133

#print axioms Cert.M133.verified
