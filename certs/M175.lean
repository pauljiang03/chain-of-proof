import ChainOfProof
open ChainOfProof

namespace Cert.M175

def cited : List Fact := [
  ⟨161, .fileCreated, 1427230620985995, 1, 42, 40⟩,
  ⟨175, .fileModified, 1247549551658939, 1, 42, 40⟩ ]

def claim : Claim := Sets.copiedHere 161 175

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M175

#print axioms Cert.M175.verified
