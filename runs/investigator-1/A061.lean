import ChainOfProof
open ChainOfProof

namespace Cert.A061

def cited : List Fact := [
  ⟨109, .fileCreated, 1427205577630000, 10000, 93, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨108, .fileCreated, 1427205567120000, 10000, 92, 69⟩,
  ⟨117, .fileCreated, 1427205584860000, 10000, 101, 69⟩,
  ⟨118, .fileCreated, 1427205606780000, 10000, 102, 69⟩,
  ⟨112, .fileCreated, 1427205579710000, 10000, 96, 69⟩,
  ⟨119, .fileCreated, 1427205612590000, 10000, 103, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 109 499) (.both (Sets.recoveredOnDevice 108 499) (.both (Sets.recoveredOnDevice 117 499) (.both (Sets.recoveredOnDevice 118 499) (.both (Sets.recoveredOnDevice 112 499) (Sets.recoveredOnDevice 119 499)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A061

#print axioms Cert.A061.verified
