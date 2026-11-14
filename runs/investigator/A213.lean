import ChainOfProof
open ChainOfProof

namespace Cert.A213

def cited : List Fact := [
  ⟨109, .fileCreated, 1427205577630000, 10000, 93, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨340, .tag, 1794614400000000, 1, 93, 198⟩,
  ⟨159, .fileModified, 1418746226000000, 10000, 51, 19⟩,
  ⟨325, .tag, 1794614400000000, 1, 51, 198⟩,
  ⟨324, .tag, 1794614400000000, 1, 51, 197⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 109 376) (.both (Sets.tagged 109 .obj 340 198) (.both (Sets.tagged 159 .obj 325 198) (.both (Sets.tagged 159 .obj 324 197) (Sets.deviceHolds 1 374))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A213

#print axioms Cert.A213.verified
