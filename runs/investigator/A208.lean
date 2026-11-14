import ChainOfProof
open ChainOfProof

namespace Cert.A208

def cited : List Fact := [
  ⟨120, .fileCreated, 1427205612970000, 10000, 104, 69⟩,
  ⟨166, .fileModified, 1420485308000000, 2000000, 104, 69⟩ ]

def claim : Claim := Sets.copiedHere 120 166

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A208

#print axioms Cert.A208.verified
