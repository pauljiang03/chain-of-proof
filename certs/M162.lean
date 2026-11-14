import ChainOfProof
open ChainOfProof

namespace Cert.M162

def cited : List Fact := [
  ⟨148, .fileCreated, 1427230540318253, 1, 131, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨212, .fileModified, 1419018826000000, 1, 131, 111⟩,
  ⟨451, .tag, 1794614400000000, 1, 131, 235⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 148 500) (.both (Sets.copiedHere 148 212) (Sets.tagged 148 .obj 451 235))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M162

#print axioms Cert.M162.verified
