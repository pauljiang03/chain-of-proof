import ChainOfProof
open ChainOfProof

namespace Cert.M190

def cited : List Fact := [
  ⟨221, .fileModified, 1420491668000000, 1, 132, 111⟩,
  ⟨452, .tag, 1794614400000000, 1, 132, 243⟩,
  ⟨149, .fileCreated, 1427230543859459, 1, 132, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨222, .fileModified, 1420491668000000, 1, 134, 111⟩,
  ⟨458, .tag, 1794614400000000, 1, 134, 243⟩,
  ⟨151, .fileCreated, 1427230543859459, 1, 134, 111⟩,
  ⟨223, .fileModified, 1420491668000000, 2000000, 103, 69⟩,
  ⟨424, .tag, 1794614400000000, 1, 103, 243⟩,
  ⟨119, .fileCreated, 1427205612590000, 10000, 103, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 221) (.both (Sets.tagged 221 .obj 452 243) (.both (Sets.recoveredOnDevice 149 500) (.both (Sets.fileModifiedAt 222) (.both (Sets.tagged 222 .obj 458 243) (.both (Sets.recoveredOnDevice 151 500) (.both (Sets.fileModifiedAt 223) (.both (Sets.tagged 223 .obj 424 243) (Sets.recoveredOnDevice 119 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M190

#print axioms Cert.M190.verified
