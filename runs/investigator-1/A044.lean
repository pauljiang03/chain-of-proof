import ChainOfProof
open ChainOfProof

namespace Cert.A044

def cited : List Fact := [
  ⟨1903, .webVisit, 1427135840514000, 1, 1240, 1095⟩,
  ⟨1906, .webVisit, 1427135901230000, 1, 1242, 1095⟩,
  ⟨1957, .webVisit, 1427142413986000, 1, 1263, 1095⟩,
  ⟨1961, .webVisit, 1427142453345000, 1, 1265, 1095⟩,
  ⟨2097, .webVisit, 1427205692336000, 1, 1339, 1095⟩,
  ⟨2163, .webVisit, 1427229858901000, 1, 1365, 1095⟩ ]

def claim : Claim := .both (Sets.visited 1903) (.both (Sets.visited 1906) (.both (Sets.visited 1957) (.both (Sets.visited 1961) (.both (Sets.visited 2097) (Sets.visited 2163)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A044

#print axioms Cert.A044.verified
