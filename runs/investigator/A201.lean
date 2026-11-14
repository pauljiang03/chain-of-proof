import ChainOfProof
open ChainOfProof

namespace Cert.A201

def cited : List Fact := [
  ⟨113, .fileCreated, 1427205580710000, 10000, 97, 69⟩,
  ⟨157, .fileModified, 1417541338000000, 2000000, 97, 69⟩ ]

def claim : Claim := Sets.copiedHere 113 157

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A201

#print axioms Cert.A201.verified
