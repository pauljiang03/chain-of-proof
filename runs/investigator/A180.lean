import ChainOfProof
open ChainOfProof

namespace Cert.A180

def cited : List Fact := [
  ⟨109, .fileCreated, 1427205577630000, 10000, 93, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 109 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A180

#print axioms Cert.A180.verified
