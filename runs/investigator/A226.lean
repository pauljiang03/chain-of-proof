import ChainOfProof
open ChainOfProof

namespace Cert.A226

def cited : List Fact := [
  ⟨85, .fileCreated, 1427144117150000, 10000, 68, 69⟩,
  ⟨154, .fileModified, 1367954382000000, 2000000, 68, 69⟩ ]

def claim : Claim := Sets.copiedHere 85 154

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A226

#print axioms Cert.A226.verified
