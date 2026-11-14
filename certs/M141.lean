import ChainOfProof
open ChainOfProof

namespace Cert.M141

def cited : List Fact := [
  ⟨127, .fileCreated, 1427230456775489, 1, 110, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨248, .fileModified, 1422046030000000, 1, 110, 111⟩,
  ⟨430, .tag, 1794614400000000, 1, 110, 233⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 127 500) (.both (Sets.copiedHere 127 248) (Sets.tagged 127 .obj 430 233))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M141

#print axioms Cert.M141.verified
