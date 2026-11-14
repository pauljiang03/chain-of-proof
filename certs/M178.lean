import ChainOfProof
open ChainOfProof

namespace Cert.M178

def cited : List Fact := [
  ⟨164, .fileCreated, 1427297313647604, 1, 45, 4⟩,
  ⟨268, .fileModified, 1427297314552404, 1, 45, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 164) (.both (Sets.fileModifiedAt 268) (.before 164 268))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M178

#print axioms Cert.M178.verified
