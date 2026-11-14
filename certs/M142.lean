import ChainOfProof
open ChainOfProof

namespace Cert.M142

def cited : List Fact := [
  ⟨128, .fileCreated, 1427230456775489, 1, 112, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨249, .fileModified, 1422046030000000, 1, 112, 111⟩,
  ⟨432, .tag, 1794614400000000, 1, 112, 233⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 128 500) (.both (Sets.copiedHere 128 249) (Sets.tagged 128 .obj 432 233))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M142

#print axioms Cert.M142.verified
