import ChainOfProof
open ChainOfProof

namespace Cert.A041

def cited : List Fact := [
  ⟨1707, .webVisit, 1427133738566209, 1, 1135, 881⟩,
  ⟨1840, .webVisit, 1427134464642450, 1, 1210, 1095⟩,
  ⟨1877, .webVisit, 1427134639898079, 1, 1227, 881⟩,
  ⟨1881, .webVisit, 1427134680896293, 1, 1229, 881⟩,
  ⟨1901, .webVisit, 1427134761977755, 1, 1239, 881⟩ ]

def claim : Claim := .both (Sets.visited 1707) (.both (Sets.visited 1840) (.both (Sets.visited 1877) (.both (Sets.visited 1881) (Sets.visited 1901))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A041

#print axioms Cert.A041.verified
