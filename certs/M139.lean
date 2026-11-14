import ChainOfProof
open ChainOfProof

namespace Cert.M139

def cited : List Fact := [
  ⟨125, .fileCreated, 1427222920734358, 1, 44, 4⟩,
  ⟨192, .fileModified, 1427223570611170, 1, 44, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 125) (.both (Sets.fileModifiedAt 192) (.before 125 192))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M139

#print axioms Cert.M139.verified
