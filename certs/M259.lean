import ChainOfProof
open ChainOfProof

namespace Cert.M259

def cited : List Fact := [
  ⟨1555, .webVisit, 1427036992405000, 1, 1104, 1095⟩,
  ⟨1556, .webVisit, 1427036994355000, 1, 1105, 1095⟩,
  ⟨1557, .webVisit, 1427036994355000, 1, 1105, 1095⟩,
  ⟨1558, .webVisit, 1427036994355000, 1, 1105, 1095⟩,
  ⟨1559, .webVisit, 1427036994355000, 1, 1105, 1095⟩,
  ⟨1560, .webVisit, 1427036996000000, 1, 1105, 881⟩,
  ⟨1561, .webVisit, 1427036996000000, 1, 1105, 881⟩,
  ⟨1562, .webVisit, 1427037023906000, 1, 1106, 1095⟩,
  ⟨1563, .webVisit, 1427037023906000, 1, 1106, 1095⟩,
  ⟨1564, .webVisit, 1427037023906000, 1, 1106, 1095⟩,
  ⟨1565, .webVisit, 1427037023906000, 1, 1106, 1095⟩,
  ⟨1566, .webVisit, 1427037024000000, 1, 1106, 881⟩,
  ⟨1567, .webVisit, 1427037024000000, 1, 1106, 881⟩,
  ⟨1568, .webVisit, 1427037048386000, 1, 1104, 1095⟩,
  ⟨1569, .webVisit, 1427037050000000, 1, 1104, 881⟩,
  ⟨1570, .webVisit, 1427037050000000, 1, 1104, 881⟩,
  ⟨1571, .webVisit, 1427037050351000, 1, 1102, 1095⟩,
  ⟨1572, .webVisit, 1427037052000000, 1, 1102, 881⟩,
  ⟨1573, .webVisit, 1427037052000000, 1, 1102, 881⟩,
  ⟨1574, .webVisit, 1427037052040000, 1, 1107, 1095⟩,
  ⟨1575, .webVisit, 1427037052040000, 1, 1107, 1095⟩,
  ⟨1576, .webVisit, 1427037052040000, 1, 1107, 1095⟩,
  ⟨1577, .webVisit, 1427037052040000, 1, 1107, 1095⟩,
  ⟨1578, .webVisit, 1427037054000000, 1, 1107, 881⟩,
  ⟨1579, .webVisit, 1427037056755000, 1, 1108, 1095⟩,
  ⟨1580, .webVisit, 1427037056755000, 1, 1108, 1095⟩,
  ⟨1581, .webVisit, 1427037056755000, 1, 1108, 1095⟩,
  ⟨1582, .webVisit, 1427037064851000, 1, 1109, 1095⟩,
  ⟨1583, .webVisit, 1427037064851000, 1, 1109, 1095⟩,
  ⟨1584, .webVisit, 1427037064851000, 1, 1109, 1095⟩,
  ⟨1585, .webVisit, 1427037064851000, 1, 1109, 1095⟩,
  ⟨1586, .webVisit, 1427037066000000, 1, 1109, 881⟩,
  ⟨1587, .webVisit, 1427037066000000, 1, 1109, 881⟩,
  ⟨1588, .webVisit, 1427037066832000, 1, 1110, 1095⟩,
  ⟨1589, .webVisit, 1427037066848000, 1, 1110, 1095⟩,
  ⟨1590, .webVisit, 1427037068000000, 1, 1110, 881⟩,
  ⟨1591, .webVisit, 1427037068000000, 1, 1110, 881⟩,
  ⟨1592, .webVisit, 1427037072199000, 1, 1108, 1095⟩,
  ⟨1593, .webVisit, 1427037074000000, 1, 1108, 881⟩,
  ⟨1594, .webVisit, 1427037074000000, 1, 1108, 881⟩ ]

def claim : Claim := .both (Sets.visited 1555) (.both (Sets.visited 1556) (.both (Sets.visited 1557) (.both (Sets.visited 1558) (.both (Sets.visited 1559) (.both (Sets.visited 1560) (.both (Sets.visited 1561) (.both (Sets.visited 1562) (.both (Sets.visited 1563) (.both (Sets.visited 1564) (.both (Sets.visited 1565) (.both (Sets.visited 1566) (.both (Sets.visited 1567) (.both (Sets.visited 1568) (.both (Sets.visited 1569) (.both (Sets.visited 1570) (.both (Sets.visited 1571) (.both (Sets.visited 1572) (.both (Sets.visited 1573) (.both (Sets.visited 1574) (.both (Sets.visited 1575) (.both (Sets.visited 1576) (.both (Sets.visited 1577) (.both (Sets.visited 1578) (.both (Sets.visited 1579) (.both (Sets.visited 1580) (.both (Sets.visited 1581) (.both (Sets.visited 1582) (.both (Sets.visited 1583) (.both (Sets.visited 1584) (.both (Sets.visited 1585) (.both (Sets.visited 1586) (.both (Sets.visited 1587) (.both (Sets.visited 1588) (.both (Sets.visited 1589) (.both (Sets.visited 1590) (.both (Sets.visited 1591) (.both (Sets.visited 1592) (.both (Sets.visited 1593) (Sets.visited 1594)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M259

#print axioms Cert.M259.verified
