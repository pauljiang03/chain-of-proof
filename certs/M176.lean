import ChainOfProof
open ChainOfProof

namespace Cert.M176

def cited : List Fact := [
  ⟨162, .fileCreated, 1427230620985995, 1, 41, 40⟩,
  ⟨176, .fileModified, 1247549551674540, 1, 41, 40⟩ ]

def claim : Claim := Sets.copiedHere 162 176

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M176

#print axioms Cert.M176.verified
