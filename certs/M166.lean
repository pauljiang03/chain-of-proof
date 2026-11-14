import ChainOfProof
open ChainOfProof

namespace Cert.M166

def cited : List Fact := [
  ⟨152, .fileCreated, 1427230543859459, 1, 135, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨219, .fileModified, 1420485308000000, 1, 135, 111⟩,
  ⟨459, .tag, 1794614400000000, 1, 135, 244⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 152 500) (.both (Sets.copiedHere 152 219) (Sets.tagged 152 .obj 459 244))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M166

#print axioms Cert.M166.verified
