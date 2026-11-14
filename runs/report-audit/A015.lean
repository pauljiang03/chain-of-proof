import ChainOfProof
open ChainOfProof

namespace Cert.A015

def cited : List Fact := [
  ⟨126, .fileCreated, 1427226707220000, 10000, 109, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 126 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A015

#print axioms Cert.A015.verified
