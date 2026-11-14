import ChainOfProof
open ChainOfProof

namespace Cert.M087

def cited : List Fact := [
  ⟨73, .fileCreated, 1427034895145933, 1, 56, 4⟩,
  ⟨98, .fileModified, 1427034899857143, 1, 56, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 73) (.both (Sets.fileModifiedAt 98) (.before 73 98))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M087

#print axioms Cert.M087.verified
