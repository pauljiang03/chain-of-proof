import ChainOfProof
open ChainOfProof

namespace Cert.M163

def cited : List Fact := [
  ⟨149, .fileCreated, 1427230543859459, 1, 132, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨221, .fileModified, 1420491668000000, 1, 132, 111⟩,
  ⟨452, .tag, 1794614400000000, 1, 132, 243⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 149 500) (.both (Sets.copiedHere 149 221) (Sets.tagged 149 .obj 452 243))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M163

#print axioms Cert.M163.verified
