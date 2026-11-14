import ChainOfProof
open ChainOfProof

namespace Cert.A070

def cited : List Fact := [
  ⟨85, .fileCreated, 1427144117150000, 10000, 68, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨107, .fileCreated, 1427144137810000, 10000, 91, 69⟩,
  ⟨126, .fileCreated, 1427226707220000, 10000, 109, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 85 499) (.both (Sets.recoveredOnDevice 107 499) (Sets.recoveredOnDevice 126 499))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A070

#print axioms Cert.A070.verified
