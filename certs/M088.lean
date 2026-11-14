import ChainOfProof
open ChainOfProof

namespace Cert.M088

def cited : List Fact := [
  ⟨74, .fileCreated, 1427037064087334, 1, 57, 4⟩,
  ⟨100, .fileModified, 1427037064851734, 1, 57, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 74) (.both (Sets.fileModifiedAt 100) (.before 74 100))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M088

#print axioms Cert.M088.verified
