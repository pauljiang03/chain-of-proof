import ChainOfProof
open ChainOfProof

namespace Cert.M136

def cited : List Fact := [
  ⟨122, .fileCreated, 1427205614340000, 10000, 106, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨232, .fileModified, 1421090426000000, 2000000, 106, 69⟩,
  ⟨427, .tag, 1794614400000000, 1, 106, 246⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 122 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 122) (.both (Sets.copiedHere 122 232) (Sets.tagged 122 .obj 427 246)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M136

#print axioms Cert.M136.verified
