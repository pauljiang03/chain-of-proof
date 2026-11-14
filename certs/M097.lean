import ChainOfProof
open ChainOfProof

namespace Cert.M097

def cited : List Fact := [
  ⟨83, .fileCreated, 1427140547296776, 1, 66, 4⟩,
  ⟨191, .fileModified, 1427140613339270, 1, 66, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 83) (.both (Sets.fileModifiedAt 191) (.before 83 191))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M097

#print axioms Cert.M097.verified
