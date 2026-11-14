import ChainOfProof
open ChainOfProof

namespace Cert.A042

def cited : List Fact := [
  ⟨1922, .webVisit, 1427140518593045, 1, 1246, 881⟩,
  ⟨1954, .webVisit, 1427141093392629, 1, 1262, 1095⟩,
  ⟨1965, .webVisit, 1427142869099416, 1, 1267, 1095⟩,
  ⟨2085, .webVisit, 1427144192855777, 1, 1333, 1095⟩ ]

def claim : Claim := .both (Sets.visited 1922) (.both (Sets.visited 1954) (.both (Sets.visited 1965) (Sets.visited 2085)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A042

#print axioms Cert.A042.verified
