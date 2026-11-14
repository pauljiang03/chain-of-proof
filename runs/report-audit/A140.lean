import ChainOfProof
open ChainOfProof

namespace Cert.A140

def cited : List Fact := [
  ⟨122, .fileCreated, 1427205614340000, 10000, 106, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 122 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A140

#print axioms Cert.A140.verified
