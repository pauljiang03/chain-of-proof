import ChainOfProof
open ChainOfProof

namespace Cert.M078

def cited : List Fact := [
  ⟨64, .fileCreated, 1247547264093319, 1, 49, 4⟩,
  ⟨173, .fileModified, 1247547264483320, 1, 49, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 64) (.both (Sets.fileModifiedAt 173) (.before 64 173))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M078

#print axioms Cert.M078.verified
