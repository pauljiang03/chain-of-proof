import ChainOfProof
open ChainOfProof

namespace Cert.A204

def cited : List Fact := [
  ⟨116, .fileCreated, 1427205584810000, 10000, 100, 69⟩,
  ⟨169, .fileModified, 1421087022000000, 2000000, 100, 69⟩ ]

def claim : Claim := Sets.copiedHere 116 169

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A204

#print axioms Cert.A204.verified
