import ChainOfProof
open ChainOfProof

namespace Cert.M263

def cited : List Fact := [
  ⟨1715, .webVisit, 1427133811261409, 1, 1139, 881⟩,
  ⟨1716, .webVisit, 1427133811261409, 1, 1139, 881⟩,
  ⟨1717, .webVisit, 1427133820424839, 1, 1140, 881⟩,
  ⟨1718, .webVisit, 1427133820424839, 1, 1140, 881⟩,
  ⟨1719, .webVisit, 1427133873578434, 1, 1141, 881⟩,
  ⟨1720, .webVisit, 1427133873578434, 1, 1141, 881⟩,
  ⟨1721, .webVisit, 1427133893773574, 1, 1142, 881⟩,
  ⟨1722, .webVisit, 1427133893773574, 1, 1142, 881⟩,
  ⟨1723, .webVisit, 1427133894864679, 1, 1143, 881⟩,
  ⟨1724, .webVisit, 1427133894864679, 1, 1143, 881⟩,
  ⟨1725, .webVisit, 1427133915865196, 1, 1144, 881⟩,
  ⟨1726, .webVisit, 1427133915865196, 1, 1144, 881⟩,
  ⟨1727, .webVisit, 1427133918131408, 1, 1145, 881⟩,
  ⟨1728, .webVisit, 1427133918131408, 1, 1145, 881⟩,
  ⟨1729, .webVisit, 1427133919638342, 1, 1146, 881⟩,
  ⟨1730, .webVisit, 1427133919638342, 1, 1146, 881⟩,
  ⟨1731, .webVisit, 1427133922229489, 1, 1147, 881⟩,
  ⟨1732, .webVisit, 1427133922229489, 1, 1147, 881⟩,
  ⟨1733, .webVisit, 1427133927714213, 1, 1148, 881⟩,
  ⟨1734, .webVisit, 1427133927714213, 1, 1148, 881⟩,
  ⟨1735, .webVisit, 1427133928926068, 1, 1149, 881⟩,
  ⟨1736, .webVisit, 1427133928926068, 1, 1149, 881⟩,
  ⟨1737, .webVisit, 1427133948655161, 1, 1150, 881⟩,
  ⟨1738, .webVisit, 1427133948655161, 1, 1150, 881⟩,
  ⟨1739, .webVisit, 1427133954821953, 1, 1151, 881⟩,
  ⟨1740, .webVisit, 1427133954821953, 1, 1151, 881⟩,
  ⟨1741, .webVisit, 1427133955442734, 1, 1152, 881⟩,
  ⟨1742, .webVisit, 1427133955442734, 1, 1152, 881⟩,
  ⟨1743, .webVisit, 1427133961146198, 1, 1153, 881⟩,
  ⟨1744, .webVisit, 1427133961146198, 1, 1153, 881⟩,
  ⟨1745, .webVisit, 1427133961439208, 1, 1154, 881⟩,
  ⟨1746, .webVisit, 1427133961439208, 1, 1154, 881⟩,
  ⟨1747, .webVisit, 1427133987545119, 1, 1155, 881⟩,
  ⟨1748, .webVisit, 1427133987545119, 1, 1155, 881⟩,
  ⟨1749, .webVisit, 1427134013440646, 1, 1156, 881⟩,
  ⟨1750, .webVisit, 1427134013440646, 1, 1156, 881⟩,
  ⟨1751, .webVisit, 1427134013795192, 1, 1157, 881⟩,
  ⟨1752, .webVisit, 1427134013795192, 1, 1157, 881⟩,
  ⟨1753, .webVisit, 1427134048329651, 1, 1158, 1095⟩,
  ⟨1754, .webVisit, 1427134065326175, 1, 1115, 1095⟩ ]

def claim : Claim := .both (Sets.visited 1715) (.both (Sets.visited 1716) (.both (Sets.visited 1717) (.both (Sets.visited 1718) (.both (Sets.visited 1719) (.both (Sets.visited 1720) (.both (Sets.visited 1721) (.both (Sets.visited 1722) (.both (Sets.visited 1723) (.both (Sets.visited 1724) (.both (Sets.visited 1725) (.both (Sets.visited 1726) (.both (Sets.visited 1727) (.both (Sets.visited 1728) (.both (Sets.visited 1729) (.both (Sets.visited 1730) (.both (Sets.visited 1731) (.both (Sets.visited 1732) (.both (Sets.visited 1733) (.both (Sets.visited 1734) (.both (Sets.visited 1735) (.both (Sets.visited 1736) (.both (Sets.visited 1737) (.both (Sets.visited 1738) (.both (Sets.visited 1739) (.both (Sets.visited 1740) (.both (Sets.visited 1741) (.both (Sets.visited 1742) (.both (Sets.visited 1743) (.both (Sets.visited 1744) (.both (Sets.visited 1745) (.both (Sets.visited 1746) (.both (Sets.visited 1747) (.both (Sets.visited 1748) (.both (Sets.visited 1749) (.both (Sets.visited 1750) (.both (Sets.visited 1751) (.both (Sets.visited 1752) (.both (Sets.visited 1753) (Sets.visited 1754)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M263

#print axioms Cert.M263.verified
