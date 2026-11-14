import ChainOfProof
open ChainOfProof

namespace Cert.A074

def cited : List Fact := [
  ⟨161, .fileCreated, 1427230620985995, 1, 42, 40⟩,
  ⟨175, .fileModified, 1247549551658939, 1, 42, 40⟩,
  ⟨162, .fileCreated, 1427230620985995, 1, 41, 40⟩,
  ⟨176, .fileModified, 1247549551674540, 1, 41, 40⟩,
  ⟨163, .fileCreated, 1427230623029598, 1, 43, 40⟩,
  ⟨177, .fileModified, 1247549551674540, 1, 43, 40⟩ ]

def claim : Claim := .both (Sets.copiedHere 161 175) (.both (Sets.copiedHere 162 176) (Sets.copiedHere 163 177))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A074

#print axioms Cert.A074.verified
