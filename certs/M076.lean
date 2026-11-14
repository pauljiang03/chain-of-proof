import ChainOfProof
open ChainOfProof

namespace Cert.M076

def cited : List Fact := [
  ⟨62, .fileCreated, 1247547263656519, 1, 47, 4⟩,
  ⟨134, .fileModified, 1247547264280521, 1, 47, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 62) (.both (Sets.fileModifiedAt 134) (.before 62 134))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M076

#print axioms Cert.M076.verified
