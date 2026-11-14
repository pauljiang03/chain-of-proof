import ChainOfProof
open ChainOfProof

namespace Cert.A066

def cited : List Fact := [
  ⟨269, .fileDeleted, 1427226707117000, 1, 144, 4⟩,
  ⟨270, .fileDeleted, 1427226707133000, 1, 145, 4⟩,
  ⟨271, .fileDeleted, 1427226707133000, 1, 146, 4⟩,
  ⟨272, .fileDeleted, 1427226707149000, 1, 147, 4⟩ ]

def claim : Claim := .both (Sets.fileDeletedAt 269) (.both (Sets.fileDeletedAt 270) (.both (Sets.fileDeletedAt 271) (Sets.fileDeletedAt 272)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A066

#print axioms Cert.A066.verified
