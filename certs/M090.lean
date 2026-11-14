import ChainOfProof
open ChainOfProof

namespace Cert.M090

def cited : List Fact := [
  ⟨76, .fileCreated, 1427037112048820, 1, 59, 4⟩,
  ⟨183, .fileModified, 1427037112048820, 1, 59, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 76) (Sets.fileModifiedAt 183)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M090

#print axioms Cert.M090.verified
