import ChainOfProof
open ChainOfProof

namespace Cert.M111

def cited : List Fact := [
  ⟨97, .fileCreated, 1427144132060000, 10000, 81, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨187, .fileModified, 1363557684000000, 2000000, 81, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 97 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 97 187)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M111

#print axioms Cert.M111.verified
