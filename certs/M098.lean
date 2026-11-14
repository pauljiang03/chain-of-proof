import ChainOfProof
open ChainOfProof

namespace Cert.M098

def cited : List Fact := [
  ⟨84, .fileCreated, 1427140590661442, 1, 67, 4⟩,
  ⟨190, .fileModified, 1427140593481297, 1, 67, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 84) (.both (Sets.fileModifiedAt 190) (.before 84 190))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M098

#print axioms Cert.M098.verified
