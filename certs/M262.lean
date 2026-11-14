import ChainOfProof
open ChainOfProof

namespace Cert.M262

def cited : List Fact := [
  ⟨1675, .webVisit, 1427131659684391, 1, 1096, 1095⟩,
  ⟨1676, .webVisit, 1427131660135592, 1, 1096, 1095⟩,
  ⟨1677, .webVisit, 1427131664923166, 1, 1124, 1095⟩,
  ⟨1678, .webVisit, 1427131665385673, 1, 1125, 1095⟩,
  ⟨1679, .webVisit, 1427131665393173, 1, 1125, 1095⟩,
  ⟨1680, .webVisit, 1427131666978197, 1, 1126, 1095⟩,
  ⟨1681, .webVisit, 1427131666978197, 1, 1126, 1095⟩,
  ⟨1682, .webVisit, 1427131667430598, 1, 1127, 1095⟩,
  ⟨1683, .webVisit, 1427131668113002, 1, 1128, 1095⟩,
  ⟨1684, .webVisit, 1427131669150000, 1, 1129, 1095⟩,
  ⟨1685, .webVisit, 1427131669150805, 1, 1129, 1095⟩,
  ⟨1686, .webVisit, 1427131669150805, 1, 1129, 1095⟩,
  ⟨1687, .webVisit, 1427131669338000, 1, 1130, 1095⟩,
  ⟨1688, .webVisit, 1427131669338005, 1, 1130, 1095⟩,
  ⟨1689, .webVisit, 1427131669353000, 1, 1094, 1095⟩,
  ⟨1690, .webVisit, 1427131670196007, 1, 1129, 1095⟩,
  ⟨1691, .webVisit, 1427131676613960, 1, 1123, 881⟩,
  ⟨1692, .webVisit, 1427131676613960, 1, 1123, 881⟩,
  ⟨1693, .webVisit, 1427131679029514, 1, 1107, 881⟩,
  ⟨1694, .webVisit, 1427131679029514, 1, 1107, 881⟩,
  ⟨1695, .webVisit, 1427131698559904, 1, 1094, 1095⟩,
  ⟨1696, .webVisit, 1427131698559904, 1, 1131, 1095⟩,
  ⟨1697, .webVisit, 1427131698559905, 1, 1115, 1095⟩,
  ⟨1698, .webVisit, 1427131698700000, 1, 1115, 1095⟩,
  ⟨1699, .webVisit, 1427131698700305, 1, 1115, 1095⟩,
  ⟨1700, .webVisit, 1427131698700305, 1, 1115, 1095⟩,
  ⟨1701, .webVisit, 1427131699817907, 1, 1132, 1095⟩,
  ⟨1702, .webVisit, 1427131735180341, 1, 1130, 1095⟩,
  ⟨1703, .webVisit, 1427133729303892, 1, 1133, 881⟩,
  ⟨1704, .webVisit, 1427133729303892, 1, 1133, 881⟩,
  ⟨1705, .webVisit, 1427133737705056, 1, 1134, 881⟩,
  ⟨1706, .webVisit, 1427133737705056, 1, 1134, 881⟩,
  ⟨1707, .webVisit, 1427133738566209, 1, 1135, 881⟩,
  ⟨1708, .webVisit, 1427133738566209, 1, 1135, 881⟩,
  ⟨1709, .webVisit, 1427133738566209, 1, 1136, 881⟩,
  ⟨1710, .webVisit, 1427133738566209, 1, 1136, 881⟩,
  ⟨1711, .webVisit, 1427133764343210, 1, 1137, 881⟩,
  ⟨1712, .webVisit, 1427133764343210, 1, 1137, 881⟩,
  ⟨1713, .webVisit, 1427133797161615, 1, 1138, 881⟩,
  ⟨1714, .webVisit, 1427133797161615, 1, 1138, 881⟩ ]

def claim : Claim := .both (Sets.visited 1675) (.both (Sets.visited 1676) (.both (Sets.visited 1677) (.both (Sets.visited 1678) (.both (Sets.visited 1679) (.both (Sets.visited 1680) (.both (Sets.visited 1681) (.both (Sets.visited 1682) (.both (Sets.visited 1683) (.both (Sets.visited 1684) (.both (Sets.visited 1685) (.both (Sets.visited 1686) (.both (Sets.visited 1687) (.both (Sets.visited 1688) (.both (Sets.visited 1689) (.both (Sets.visited 1690) (.both (Sets.visited 1691) (.both (Sets.visited 1692) (.both (Sets.visited 1693) (.both (Sets.visited 1694) (.both (Sets.visited 1695) (.both (Sets.visited 1696) (.both (Sets.visited 1697) (.both (Sets.visited 1698) (.both (Sets.visited 1699) (.both (Sets.visited 1700) (.both (Sets.visited 1701) (.both (Sets.visited 1702) (.both (Sets.visited 1703) (.both (Sets.visited 1704) (.both (Sets.visited 1705) (.both (Sets.visited 1706) (.both (Sets.visited 1707) (.both (Sets.visited 1708) (.both (Sets.visited 1709) (.both (Sets.visited 1710) (.both (Sets.visited 1711) (.both (Sets.visited 1712) (.both (Sets.visited 1713) (Sets.visited 1714)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M262

#print axioms Cert.M262.verified
