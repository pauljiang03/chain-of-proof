import ChainOfProof
open ChainOfProof

namespace Cert.M085

def cited : List Fact := [
  ⟨71, .fileCreated, 1427034895052334, 1, 54, 4⟩,
  ⟨97, .fileModified, 1427034899825943, 1, 54, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 71) (.both (Sets.fileModifiedAt 97) (.before 71 97))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M085

#print axioms Cert.M085.verified
