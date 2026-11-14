import ChainOfProof
open ChainOfProof

namespace Cert.M141

def cited : List Fact := [
  ⟨127, .fileCreated, 1427297313647604, 1, 45, 4⟩,
  ⟨194, .fileModified, 1427297314552404, 1, 45, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 127) (.both (Sets.fileModifiedAt 194) (.before 127 194))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M141

#print axioms Cert.M141.verified
