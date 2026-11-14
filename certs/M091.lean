import ChainOfProof
open ChainOfProof

namespace Cert.M091

def cited : List Fact := [
  ⟨77, .fileCreated, 1427039636431332, 1, 60, 4⟩,
  ⟨184, .fileModified, 1427039642655743, 1, 60, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 77) (.both (Sets.fileModifiedAt 184) (.before 77 184))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M091

#print axioms Cert.M091.verified
