import ChainOfProof
open ChainOfProof

namespace Cert.A134

def cited : List Fact := [
  ⟨116, .fileCreated, 1427205584810000, 10000, 100, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 116 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A134

#print axioms Cert.A134.verified
