import ChainOfProof
open ChainOfProof

namespace Cert.M093

def cited : List Fact := [
  ⟨79, .fileCreated, 1427039636478132, 1, 62, 4⟩,
  ⟨259, .fileModified, 1427039642686943, 1, 62, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 79) (.both (Sets.fileModifiedAt 259) (.before 79 259))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M093

#print axioms Cert.M093.verified
