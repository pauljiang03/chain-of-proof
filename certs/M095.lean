import ChainOfProof
open ChainOfProof

namespace Cert.M095

def cited : List Fact := [
  ⟨81, .fileCreated, 1427039762297871, 1, 64, 4⟩,
  ⟨108, .fileModified, 1427039767071480, 1, 64, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 81) (.both (Sets.fileModifiedAt 108) (.before 81 108))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M095

#print axioms Cert.M095.verified
