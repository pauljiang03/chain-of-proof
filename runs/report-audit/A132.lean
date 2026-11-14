import ChainOfProof
open ChainOfProof

namespace Cert.A132

def cited : List Fact := [
  ⟨114, .fileCreated, 1427205583520000, 10000, 98, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 114 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A132

#print axioms Cert.A132.verified
