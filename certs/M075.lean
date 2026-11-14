import ChainOfProof
open ChainOfProof

namespace Cert.M075

def cited : List Fact := [
  ⟨61, .fileCreated, 1247547263656519, 1, 46, 4⟩,
  ⟨133, .fileModified, 1247547264280521, 1, 46, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 61) (.both (Sets.fileModifiedAt 133) (.before 61 133))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M075

#print axioms Cert.M075.verified
