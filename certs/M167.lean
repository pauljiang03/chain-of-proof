import ChainOfProof
open ChainOfProof

namespace Cert.M167

def cited : List Fact := [
  ⟨153, .fileCreated, 1427230543968659, 1, 136, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨233, .fileModified, 1421097940000000, 1, 136, 111⟩,
  ⟨454, .tag, 1794614400000000, 1, 136, 245⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 153 500) (.both (Sets.copiedHere 153 233) (Sets.tagged 153 .obj 454 245))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M167

#print axioms Cert.M167.verified
