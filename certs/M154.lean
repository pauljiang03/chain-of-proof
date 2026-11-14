import ChainOfProof
open ChainOfProof

namespace Cert.M154

def cited : List Fact := [
  ⟨140, .fileCreated, 1427230519071016, 1, 123, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨240, .fileModified, 1421766824000000, 1, 123, 111⟩,
  ⟨445, .tag, 1794614400000000, 1, 123, 240⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 140 500) (.both (Sets.copiedHere 140 240) (Sets.tagged 140 .obj 445 240))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M154

#print axioms Cert.M154.verified
