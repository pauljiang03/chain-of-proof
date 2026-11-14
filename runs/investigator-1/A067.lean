import ChainOfProof
open ChainOfProof

namespace Cert.A067

def cited : List Fact := [
  ⟨278, .fileDeleted, 1427227902851000, 1, 153, 4⟩,
  ⟨280, .fileDeleted, 1427227902851000, 1, 155, 4⟩,
  ⟨281, .fileDeleted, 1427227902851000, 1, 156, 4⟩,
  ⟨276, .fileDeleted, 1427227902851000, 1, 151, 4⟩ ]

def claim : Claim := .both (Sets.fileDeletedAt 278) (.both (Sets.fileDeletedAt 280) (.both (Sets.fileDeletedAt 281) (Sets.fileDeletedAt 276)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A067

#print axioms Cert.A067.verified
