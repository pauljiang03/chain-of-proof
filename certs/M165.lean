import ChainOfProof
open ChainOfProof

namespace Cert.M165

def cited : List Fact := [
  ⟨151, .fileCreated, 1427230543859459, 1, 134, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨222, .fileModified, 1420491668000000, 1, 134, 111⟩,
  ⟨458, .tag, 1794614400000000, 1, 134, 243⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 151 500) (.both (Sets.copiedHere 151 222) (Sets.tagged 151 .obj 458 243))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M165

#print axioms Cert.M165.verified
