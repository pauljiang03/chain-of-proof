import ChainOfProof
open ChainOfProof

namespace Cert.A071

def cited : List Fact := [
  ⟨199, .fileDeleted, 1427227902836000, 1, 114, 4⟩,
  ⟨200, .fileDeleted, 1427227902836000, 1, 115, 4⟩,
  ⟨201, .fileDeleted, 1427227902851000, 1, 116, 4⟩,
  ⟨202, .fileDeleted, 1427227902851000, 1, 117, 4⟩,
  ⟨203, .fileDeleted, 1427227902851000, 1, 118, 4⟩,
  ⟨204, .fileDeleted, 1427227902851000, 1, 119, 4⟩,
  ⟨205, .fileDeleted, 1427227902851000, 1, 120, 4⟩,
  ⟨206, .fileDeleted, 1427227902851000, 1, 121, 4⟩,
  ⟨207, .fileDeleted, 1427227902851000, 1, 122, 4⟩,
  ⟨208, .fileDeleted, 1427227902851000, 1, 123, 4⟩ ]

def claim : Claim := .both (Sets.fileDeletedAt 199) (.both (Sets.fileDeletedAt 200) (.both (Sets.fileDeletedAt 201) (.both (Sets.fileDeletedAt 202) (.both (Sets.fileDeletedAt 203) (.both (Sets.fileDeletedAt 204) (.both (Sets.fileDeletedAt 205) (.both (Sets.fileDeletedAt 206) (.both (Sets.fileDeletedAt 207) (Sets.fileDeletedAt 208)))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A071

#print axioms Cert.A071.verified
