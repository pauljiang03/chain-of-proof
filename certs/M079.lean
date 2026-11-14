import ChainOfProof
open ChainOfProof

namespace Cert.M079

def cited : List Fact := [
  ⟨65, .fileCreated, 1247547264093319, 1, 50, 4⟩,
  ⟨137, .fileModified, 1247547264483320, 1, 50, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 65) (.both (Sets.fileModifiedAt 137) (.before 65 137))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M079

#print axioms Cert.M079.verified
