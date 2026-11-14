import ChainOfProof
open ChainOfProof

namespace Cert.M086

def cited : List Fact := [
  ⟨72, .fileCreated, 1427034895067934, 1, 55, 4⟩,
  ⟨254, .fileModified, 1427034899872744, 1, 55, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 72) (.both (Sets.fileModifiedAt 254) (.before 72 254))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M086

#print axioms Cert.M086.verified
