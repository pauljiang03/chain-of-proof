import ChainOfProof
open ChainOfProof

namespace Cert.A203

def cited : List Fact := [
  ⟨115, .fileCreated, 1427205583550000, 10000, 99, 69⟩,
  ⟨165, .fileModified, 1420473442000000, 2000000, 99, 69⟩ ]

def claim : Claim := Sets.copiedHere 115 165

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A203

#print axioms Cert.A203.verified
