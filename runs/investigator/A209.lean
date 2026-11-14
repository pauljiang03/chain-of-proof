import ChainOfProof
open ChainOfProof

namespace Cert.A209

def cited : List Fact := [
  ⟨121, .fileCreated, 1427205613550000, 10000, 105, 69⟩,
  ⟨171, .fileModified, 1421097940000000, 2000000, 105, 69⟩ ]

def claim : Claim := Sets.copiedHere 121 171

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A209

#print axioms Cert.A209.verified
