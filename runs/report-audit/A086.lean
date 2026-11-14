import ChainOfProof
open ChainOfProof

namespace Cert.A086

def cited : List Fact := [
  ⟨118, .fileCreated, 1427205606780000, 10000, 102, 69⟩,
  ⟨164, .fileModified, 1419018826000000, 2000000, 102, 69⟩ ]

def claim : Claim := Sets.copiedHere 118 164

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A086

#print axioms Cert.A086.verified
