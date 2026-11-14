import ChainOfProof
open ChainOfProof

namespace Cert.M100

def cited : List Fact := [
  ⟨86, .fileCreated, 1427297313647604, 1, 45, 4⟩,
  ⟨112, .fileModified, 1427297314552404, 1, 45, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 86) (.both (Sets.fileModifiedAt 112) (.before 86 112))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M100

#print axioms Cert.M100.verified
