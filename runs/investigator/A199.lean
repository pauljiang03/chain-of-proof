import ChainOfProof
open ChainOfProof

namespace Cert.A199

def cited : List Fact := [
  ⟨111, .fileCreated, 1427205579680000, 10000, 95, 69⟩,
  ⟨168, .fileModified, 1420751304000000, 2000000, 95, 69⟩ ]

def claim : Claim := Sets.copiedHere 111 168

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A199

#print axioms Cert.A199.verified
