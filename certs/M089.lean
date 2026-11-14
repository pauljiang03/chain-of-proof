import ChainOfProof
open ChainOfProof

namespace Cert.M089

def cited : List Fact := [
  ⟨75, .fileCreated, 1427037112048820, 1, 58, 4⟩,
  ⟨101, .fileModified, 1427037112048820, 1, 58, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 75) (Sets.fileModifiedAt 101)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M089

#print axioms Cert.M089.verified
