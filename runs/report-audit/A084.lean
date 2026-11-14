import ChainOfProof
open ChainOfProof

namespace Cert.A084

def cited : List Fact := [
  ⟨109, .fileCreated, 1427205577630000, 10000, 93, 69⟩,
  ⟨160, .fileModified, 1418746226000000, 2000000, 93, 69⟩ ]

def claim : Claim := Sets.copiedHere 109 160

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A084

#print axioms Cert.A084.verified
