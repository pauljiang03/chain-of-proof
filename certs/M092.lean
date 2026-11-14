import ChainOfProof
open ChainOfProof

namespace Cert.M092

def cited : List Fact := [
  ⟨78, .fileCreated, 1427039636446932, 1, 61, 4⟩,
  ⟨105, .fileModified, 1427039642702543, 1, 61, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 78) (.both (Sets.fileModifiedAt 105) (.before 78 105))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M092

#print axioms Cert.M092.verified
