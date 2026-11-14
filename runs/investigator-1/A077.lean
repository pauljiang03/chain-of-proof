import ChainOfProof
open ChainOfProof

namespace Cert.A077

def cited : List Fact := [
  ⟨129, .fileCreated, 1427230482676152, 1, 34, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨130, .fileCreated, 1427230482676152, 1, 113, 111⟩,
  ⟨127, .fileCreated, 1427230456775489, 1, 110, 111⟩,
  ⟨145, .fileCreated, 1427230522908622, 1, 128, 111⟩,
  ⟨147, .fileCreated, 1427230540318253, 1, 130, 111⟩,
  ⟨131, .fileCreated, 1427230501021784, 1, 114, 111⟩,
  ⟨149, .fileCreated, 1427230543859459, 1, 132, 111⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 129 500) (.both (Sets.recoveredOnDevice 130 500) (.both (Sets.recoveredOnDevice 127 500) (.both (Sets.recoveredOnDevice 145 500) (.both (Sets.recoveredOnDevice 147 500) (.both (Sets.recoveredOnDevice 131 500) (Sets.recoveredOnDevice 149 500))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A077

#print axioms Cert.A077.verified
