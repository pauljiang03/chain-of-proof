import ChainOfProof
open ChainOfProof

namespace Cert.M155

def cited : List Fact := [
  ⟨141, .fileCreated, 1427230519305016, 1, 124, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨215, .fileModified, 1420473442000000, 1, 124, 111⟩,
  ⟨443, .tag, 1794614400000000, 1, 124, 241⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 141 500) (.both (Sets.copiedHere 141 215) (Sets.tagged 141 .obj 443 241))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M155

#print axioms Cert.M155.verified
