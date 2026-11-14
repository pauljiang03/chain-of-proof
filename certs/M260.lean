import ChainOfProof
open ChainOfProof

namespace Cert.M260

def cited : List Fact := [
  ⟨1595, .webVisit, 1427037074717000, 1, 1111, 1095⟩,
  ⟨1596, .webVisit, 1427037074717000, 1, 1111, 1095⟩,
  ⟨1597, .webVisit, 1427037074732000, 1, 1111, 1095⟩,
  ⟨1598, .webVisit, 1427037074732000, 1, 1111, 1095⟩,
  ⟨1599, .webVisit, 1427037076000000, 1, 1111, 881⟩,
  ⟨1600, .webVisit, 1427037076000000, 1, 1111, 881⟩,
  ⟨1601, .webVisit, 1427037118280842, 1, 1112, 881⟩,
  ⟨1602, .webVisit, 1427037118280842, 1, 1112, 881⟩,
  ⟨1603, .webVisit, 1427037118280842, 1, 1113, 881⟩,
  ⟨1604, .webVisit, 1427037118280842, 1, 1113, 881⟩,
  ⟨1605, .webVisit, 1427037127185577, 1, 1114, 881⟩,
  ⟨1606, .webVisit, 1427037127185577, 1, 1114, 881⟩,
  ⟨1607, .webVisit, 1427037130849979, 1, 1115, 881⟩,
  ⟨1608, .webVisit, 1427037130849979, 1, 1115, 881⟩,
  ⟨1609, .webVisit, 1427037130851427, 1, 1115, 881⟩,
  ⟨1610, .webVisit, 1427037861900252, 1, 1109, 1095⟩,
  ⟨1611, .webVisit, 1427037861900252, 1, 1098, 1095⟩,
  ⟨1612, .webVisit, 1427037861900252, 1, 1097, 1095⟩,
  ⟨1613, .webVisit, 1427037861900252, 1, 1104, 1095⟩,
  ⟨1614, .webVisit, 1427037861900252, 1, 1106, 1095⟩,
  ⟨1615, .webVisit, 1427037861900252, 1, 1099, 1095⟩,
  ⟨1616, .webVisit, 1427037861900252, 1, 1103, 1095⟩,
  ⟨1617, .webVisit, 1427037861900252, 1, 1105, 1095⟩,
  ⟨1618, .webVisit, 1427037861900252, 1, 1110, 1095⟩,
  ⟨1619, .webVisit, 1427037861900252, 1, 1100, 1095⟩,
  ⟨1620, .webVisit, 1427037861900252, 1, 1111, 1095⟩,
  ⟨1621, .webVisit, 1427037861900252, 1, 1108, 1095⟩,
  ⟨1622, .webVisit, 1427037861900252, 1, 1101, 1095⟩,
  ⟨1623, .webVisit, 1427037861900252, 1, 1102, 1095⟩,
  ⟨1624, .webVisit, 1427037861900252, 1, 1107, 1095⟩,
  ⟨1625, .webVisit, 1427037863631855, 1, 1110, 1095⟩,
  ⟨1626, .webVisit, 1427037863631855, 1, 1100, 1095⟩,
  ⟨1627, .webVisit, 1427037863631855, 1, 1111, 1095⟩,
  ⟨1628, .webVisit, 1427037863631855, 1, 1108, 1095⟩,
  ⟨1629, .webVisit, 1427037863631855, 1, 1102, 1095⟩,
  ⟨1630, .webVisit, 1427037863631855, 1, 1107, 1095⟩,
  ⟨1631, .webVisit, 1427037863647455, 1, 1109, 1095⟩,
  ⟨1632, .webVisit, 1427037863647455, 1, 1098, 1095⟩,
  ⟨1633, .webVisit, 1427037863647455, 1, 1097, 1095⟩,
  ⟨1634, .webVisit, 1427037863647455, 1, 1104, 1095⟩ ]

def claim : Claim := .both (Sets.visited 1595) (.both (Sets.visited 1596) (.both (Sets.visited 1597) (.both (Sets.visited 1598) (.both (Sets.visited 1599) (.both (Sets.visited 1600) (.both (Sets.visited 1601) (.both (Sets.visited 1602) (.both (Sets.visited 1603) (.both (Sets.visited 1604) (.both (Sets.visited 1605) (.both (Sets.visited 1606) (.both (Sets.visited 1607) (.both (Sets.visited 1608) (.both (Sets.visited 1609) (.both (Sets.visited 1610) (.both (Sets.visited 1611) (.both (Sets.visited 1612) (.both (Sets.visited 1613) (.both (Sets.visited 1614) (.both (Sets.visited 1615) (.both (Sets.visited 1616) (.both (Sets.visited 1617) (.both (Sets.visited 1618) (.both (Sets.visited 1619) (.both (Sets.visited 1620) (.both (Sets.visited 1621) (.both (Sets.visited 1622) (.both (Sets.visited 1623) (.both (Sets.visited 1624) (.both (Sets.visited 1625) (.both (Sets.visited 1626) (.both (Sets.visited 1627) (.both (Sets.visited 1628) (.both (Sets.visited 1629) (.both (Sets.visited 1630) (.both (Sets.visited 1631) (.both (Sets.visited 1632) (.both (Sets.visited 1633) (Sets.visited 1634)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M260

#print axioms Cert.M260.verified
