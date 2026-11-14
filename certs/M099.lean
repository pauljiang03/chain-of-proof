import ChainOfProof
open ChainOfProof

namespace Cert.M099

def cited : List Fact := [
  ⟨85, .fileCreated, 1427222920734358, 1, 44, 4⟩,
  ⟨111, .fileModified, 1427223570611170, 1, 44, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 85) (.both (Sets.fileModifiedAt 111) (.before 85 111))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M099

#print axioms Cert.M099.verified
