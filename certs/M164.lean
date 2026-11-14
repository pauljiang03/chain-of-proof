import ChainOfProof
open ChainOfProof

namespace Cert.M164

def cited : List Fact := [
  ⟨150, .fileCreated, 1427230543859459, 1, 133, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨218, .fileModified, 1420485308000000, 1, 133, 111⟩,
  ⟨453, .tag, 1794614400000000, 1, 133, 244⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 150 500) (.both (Sets.copiedHere 150 218) (Sets.tagged 150 .obj 453 244))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M164

#print axioms Cert.M164.verified
