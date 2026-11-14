import ChainOfProof
open ChainOfProof

namespace Cert.A043

def cited : List Fact := [
  ⟨2190, .webVisit, 1427294819528000, 1, 1376, 1095⟩,
  ⟨2219, .webVisit, 1427294854774505, 1, 1396, 1095⟩,
  ⟨2226, .webVisit, 1427294875942305, 1, 1401, 1095⟩,
  ⟨2233, .webVisit, 1427294902751205, 1, 1404, 1095⟩,
  ⟨2249, .webVisit, 1427296928809005, 1, 1409, 1095⟩ ]

def claim : Claim := .both (Sets.visited 2190) (.both (Sets.visited 2219) (.both (Sets.visited 2226) (.both (Sets.visited 2233) (Sets.visited 2249))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A043

#print axioms Cert.A043.verified
