import ChainOfProof
open ChainOfProof

namespace Cert.A070

def cited : List Fact := [
  ⟨195, .fileDeleted, 1427226707117000, 1, 110, 4⟩,
  ⟨196, .fileDeleted, 1427226707133000, 1, 111, 4⟩,
  ⟨197, .fileDeleted, 1427226707133000, 1, 112, 4⟩,
  ⟨198, .fileDeleted, 1427226707149000, 1, 113, 4⟩ ]

def claim : Claim := .both (Sets.fileDeletedAt 195) (.both (Sets.fileDeletedAt 196) (.both (Sets.fileDeletedAt 197) (Sets.fileDeletedAt 198)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A070

#print axioms Cert.A070.verified
