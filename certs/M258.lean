import ChainOfProof
open ChainOfProof

namespace Cert.M258

def cited : List Fact := [
  ⟨1515, .webVisit, 1427036941607000, 1, 1094, 1095⟩,
  ⟨1516, .webVisit, 1427036942000000, 1, 1094, 881⟩,
  ⟨1517, .webVisit, 1427036942000000, 1, 1094, 881⟩,
  ⟨1518, .webVisit, 1427036942996000, 1, 1096, 1095⟩,
  ⟨1519, .webVisit, 1427036943027000, 1, 1096, 1095⟩,
  ⟨1520, .webVisit, 1427036958596000, 1, 1097, 1095⟩,
  ⟨1521, .webVisit, 1427036958611000, 1, 1097, 1095⟩,
  ⟨1522, .webVisit, 1427036959001000, 1, 1098, 1095⟩,
  ⟨1523, .webVisit, 1427036959017000, 1, 1098, 1095⟩,
  ⟨1524, .webVisit, 1427036960000000, 1, 1098, 881⟩,
  ⟨1525, .webVisit, 1427036960000000, 1, 1098, 881⟩,
  ⟨1526, .webVisit, 1427036960000000, 1, 1097, 881⟩,
  ⟨1527, .webVisit, 1427036960000000, 1, 1097, 881⟩,
  ⟨1528, .webVisit, 1427036961185000, 1, 1099, 1095⟩,
  ⟨1529, .webVisit, 1427036961185000, 1, 1099, 1095⟩,
  ⟨1530, .webVisit, 1427036961201000, 1, 1099, 1095⟩,
  ⟨1531, .webVisit, 1427036961295000, 1, 1099, 1095⟩,
  ⟨1532, .webVisit, 1427036962000000, 1, 1099, 881⟩,
  ⟨1533, .webVisit, 1427036962000000, 1, 1099, 881⟩,
  ⟨1534, .webVisit, 1427036963494000, 1, 1096, 1095⟩,
  ⟨1535, .webVisit, 1427036964000000, 1, 1096, 881⟩,
  ⟨1536, .webVisit, 1427036964000000, 1, 1096, 881⟩,
  ⟨1537, .webVisit, 1427036978184000, 1, 1100, 1095⟩,
  ⟨1538, .webVisit, 1427036978199000, 1, 1100, 1095⟩,
  ⟨1539, .webVisit, 1427036978199000, 1, 1100, 1095⟩,
  ⟨1540, .webVisit, 1427036978308000, 1, 1100, 1095⟩,
  ⟨1541, .webVisit, 1427036980000000, 1, 1100, 881⟩,
  ⟨1542, .webVisit, 1427036980000000, 1, 1100, 881⟩,
  ⟨1543, .webVisit, 1427036987902000, 1, 1101, 1095⟩,
  ⟨1544, .webVisit, 1427036988513000, 1, 1102, 1095⟩,
  ⟨1545, .webVisit, 1427036988513000, 1, 1102, 1095⟩,
  ⟨1546, .webVisit, 1427036988513000, 1, 1102, 1095⟩,
  ⟨1547, .webVisit, 1427036991243000, 1, 1103, 1095⟩,
  ⟨1548, .webVisit, 1427036991243000, 1, 1103, 1095⟩,
  ⟨1549, .webVisit, 1427036991243000, 1, 1103, 1095⟩,
  ⟨1550, .webVisit, 1427036991274000, 1, 1103, 1095⟩,
  ⟨1551, .webVisit, 1427036992000000, 1, 1103, 881⟩,
  ⟨1552, .webVisit, 1427036992000000, 1, 1103, 881⟩,
  ⟨1553, .webVisit, 1427036992405000, 1, 1104, 1095⟩,
  ⟨1554, .webVisit, 1427036992405000, 1, 1104, 1095⟩ ]

def claim : Claim := .both (Sets.visited 1515) (.both (Sets.visited 1516) (.both (Sets.visited 1517) (.both (Sets.visited 1518) (.both (Sets.visited 1519) (.both (Sets.visited 1520) (.both (Sets.visited 1521) (.both (Sets.visited 1522) (.both (Sets.visited 1523) (.both (Sets.visited 1524) (.both (Sets.visited 1525) (.both (Sets.visited 1526) (.both (Sets.visited 1527) (.both (Sets.visited 1528) (.both (Sets.visited 1529) (.both (Sets.visited 1530) (.both (Sets.visited 1531) (.both (Sets.visited 1532) (.both (Sets.visited 1533) (.both (Sets.visited 1534) (.both (Sets.visited 1535) (.both (Sets.visited 1536) (.both (Sets.visited 1537) (.both (Sets.visited 1538) (.both (Sets.visited 1539) (.both (Sets.visited 1540) (.both (Sets.visited 1541) (.both (Sets.visited 1542) (.both (Sets.visited 1543) (.both (Sets.visited 1544) (.both (Sets.visited 1545) (.both (Sets.visited 1546) (.both (Sets.visited 1547) (.both (Sets.visited 1548) (.both (Sets.visited 1549) (.both (Sets.visited 1550) (.both (Sets.visited 1551) (.both (Sets.visited 1552) (.both (Sets.visited 1553) (Sets.visited 1554)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M258

#print axioms Cert.M258.verified
