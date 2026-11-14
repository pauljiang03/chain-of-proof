import ChainOfProof
open ChainOfProof

namespace Cert.M261

def cited : List Fact := [
  ⟨1635, .webVisit, 1427037863647455, 1, 1106, 1095⟩,
  ⟨1636, .webVisit, 1427037863647455, 1, 1099, 1095⟩,
  ⟨1637, .webVisit, 1427037863647455, 1, 1103, 1095⟩,
  ⟨1638, .webVisit, 1427037863647455, 1, 1105, 1095⟩,
  ⟨1639, .webVisit, 1427038049894889, 1, 1115, 881⟩,
  ⟨1640, .webVisit, 1427038049894889, 1, 1115, 881⟩,
  ⟨1641, .webVisit, 1427038050380690, 1, 1114, 881⟩,
  ⟨1642, .webVisit, 1427038050380690, 1, 1114, 881⟩,
  ⟨1643, .webVisit, 1427038079597811, 1, 1116, 881⟩,
  ⟨1644, .webVisit, 1427038079597811, 1, 1116, 881⟩,
  ⟨1645, .webVisit, 1427038093944581, 1, 1117, 881⟩,
  ⟨1646, .webVisit, 1427038093944581, 1, 1117, 881⟩,
  ⟨1647, .webVisit, 1427038096952834, 1, 1116, 881⟩,
  ⟨1648, .webVisit, 1427038096952834, 1, 1116, 881⟩,
  ⟨1649, .webVisit, 1427038098030650, 1, 1107, 881⟩,
  ⟨1650, .webVisit, 1427038098030650, 1, 1107, 881⟩,
  ⟨1651, .webVisit, 1427039327986000, 1, 1118, 1095⟩,
  ⟨1652, .webVisit, 1427039638786936, 1, 1119, 1095⟩,
  ⟨1653, .webVisit, 1427039728483243, 1, 1112, 881⟩,
  ⟨1654, .webVisit, 1427039728483243, 1, 1112, 881⟩,
  ⟨1655, .webVisit, 1427039728483243, 1, 1113, 881⟩,
  ⟨1656, .webVisit, 1427039728483243, 1, 1113, 881⟩,
  ⟨1657, .webVisit, 1427039740587310, 1, 1120, 881⟩,
  ⟨1658, .webVisit, 1427039740587310, 1, 1120, 881⟩,
  ⟨1659, .webVisit, 1427039744335027, 1, 1121, 881⟩,
  ⟨1660, .webVisit, 1427039744335027, 1, 1121, 881⟩,
  ⟨1661, .webVisit, 1427039763592672, 1, 1119, 1095⟩,
  ⟨1662, .webVisit, 1427039851004000, 1, 1122, 1095⟩,
  ⟨1663, .webVisit, 1427039851004448, 1, 1122, 1095⟩,
  ⟨1664, .webVisit, 1427131592706480, 1, 1118, 1095⟩,
  ⟨1665, .webVisit, 1427131618058412, 1, 1115, 881⟩,
  ⟨1666, .webVisit, 1427131618058412, 1, 1115, 881⟩,
  ⟨1667, .webVisit, 1427131618152496, 1, 1107, 881⟩,
  ⟨1668, .webVisit, 1427131618152496, 1, 1107, 881⟩,
  ⟨1669, .webVisit, 1427131625838400, 1, 1123, 881⟩,
  ⟨1670, .webVisit, 1427131625838400, 1, 1123, 881⟩,
  ⟨1671, .webVisit, 1427131638647496, 1, 1107, 881⟩,
  ⟨1672, .webVisit, 1427131638647496, 1, 1107, 881⟩,
  ⟨1673, .webVisit, 1427131656564385, 1, 1094, 1095⟩,
  ⟨1674, .webVisit, 1427131659684000, 1, 1096, 1095⟩ ]

def claim : Claim := .both (Sets.visited 1635) (.both (Sets.visited 1636) (.both (Sets.visited 1637) (.both (Sets.visited 1638) (.both (Sets.visited 1639) (.both (Sets.visited 1640) (.both (Sets.visited 1641) (.both (Sets.visited 1642) (.both (Sets.visited 1643) (.both (Sets.visited 1644) (.both (Sets.visited 1645) (.both (Sets.visited 1646) (.both (Sets.visited 1647) (.both (Sets.visited 1648) (.both (Sets.visited 1649) (.both (Sets.visited 1650) (.both (Sets.visited 1651) (.both (Sets.visited 1652) (.both (Sets.visited 1653) (.both (Sets.visited 1654) (.both (Sets.visited 1655) (.both (Sets.visited 1656) (.both (Sets.visited 1657) (.both (Sets.visited 1658) (.both (Sets.visited 1659) (.both (Sets.visited 1660) (.both (Sets.visited 1661) (.both (Sets.visited 1662) (.both (Sets.visited 1663) (.both (Sets.visited 1664) (.both (Sets.visited 1665) (.both (Sets.visited 1666) (.both (Sets.visited 1667) (.both (Sets.visited 1668) (.both (Sets.visited 1669) (.both (Sets.visited 1670) (.both (Sets.visited 1671) (.both (Sets.visited 1672) (.both (Sets.visited 1673) (Sets.visited 1674)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M261

#print axioms Cert.M261.verified
