import ChainOfProof
open ChainOfProof

namespace Cert.M265

def cited : List Fact := [
  ⟨1795, .webVisit, 1427134270411043, 1, 1183, 1095⟩,
  ⟨1796, .webVisit, 1427134270411043, 1, 1184, 1095⟩,
  ⟨1797, .webVisit, 1427134270482044, 1, 1185, 1095⟩,
  ⟨1798, .webVisit, 1427134270487044, 1, 1185, 1095⟩,
  ⟨1799, .webVisit, 1427134272341579, 1, 1186, 1095⟩,
  ⟨1800, .webVisit, 1427134272356579, 1, 1187, 1095⟩,
  ⟨1801, .webVisit, 1427134272887588, 1, 1188, 1095⟩,
  ⟨1802, .webVisit, 1427134272889588, 1, 1188, 1095⟩,
  ⟨1803, .webVisit, 1427134272889588, 1, 1188, 1095⟩,
  ⟨1804, .webVisit, 1427134272898588, 1, 1188, 1095⟩,
  ⟨1805, .webVisit, 1427134272988592, 1, 1189, 1095⟩,
  ⟨1806, .webVisit, 1427134273003592, 1, 1190, 1095⟩,
  ⟨1807, .webVisit, 1427134273018592, 1, 1191, 1095⟩,
  ⟨1808, .webVisit, 1427134273123594, 1, 1192, 1095⟩,
  ⟨1809, .webVisit, 1427134274957614, 1, 1193, 1095⟩,
  ⟨1810, .webVisit, 1427134310582692, 1, 1194, 1095⟩,
  ⟨1811, .webVisit, 1427134312474698, 1, 1195, 1095⟩,
  ⟨1812, .webVisit, 1427134327649000, 1, 1196, 1095⟩,
  ⟨1813, .webVisit, 1427134327649223, 1, 1196, 1095⟩,
  ⟨1814, .webVisit, 1427134327649223, 1, 1196, 1095⟩,
  ⟨1815, .webVisit, 1427134328194224, 1, 1196, 1095⟩,
  ⟨1816, .webVisit, 1427134355567263, 1, 1197, 1095⟩,
  ⟨1817, .webVisit, 1427134357697268, 1, 1198, 1095⟩,
  ⟨1818, .webVisit, 1427134362433278, 1, 1199, 1095⟩,
  ⟨1819, .webVisit, 1427134363575281, 1, 1200, 1095⟩,
  ⟨1820, .webVisit, 1427134365477000, 1, 1201, 1095⟩,
  ⟨1821, .webVisit, 1427134365477284, 1, 1201, 1095⟩,
  ⟨1822, .webVisit, 1427134365477284, 1, 1201, 1095⟩,
  ⟨1823, .webVisit, 1427134372231296, 1, 1202, 1095⟩,
  ⟨1824, .webVisit, 1427134372241000, 1, 1202, 1095⟩,
  ⟨1825, .webVisit, 1427134372241296, 1, 1202, 1095⟩,
  ⟨1826, .webVisit, 1427134372683301, 1, 1201, 1095⟩,
  ⟨1827, .webVisit, 1427134377501308, 1, 1202, 1095⟩,
  ⟨1828, .webVisit, 1427134400892344, 1, 1203, 1095⟩,
  ⟨1829, .webVisit, 1427134402366349, 1, 1204, 1095⟩,
  ⟨1830, .webVisit, 1427134417494372, 1, 1205, 1095⟩,
  ⟨1831, .webVisit, 1427134420073879, 1, 1206, 1095⟩,
  ⟨1832, .webVisit, 1427134437502000, 1, 1207, 1095⟩,
  ⟨1833, .webVisit, 1427134437502906, 1, 1207, 1095⟩,
  ⟨1834, .webVisit, 1427134437502906, 1, 1207, 1095⟩ ]

def claim : Claim := .both (Sets.visited 1795) (.both (Sets.visited 1796) (.both (Sets.visited 1797) (.both (Sets.visited 1798) (.both (Sets.visited 1799) (.both (Sets.visited 1800) (.both (Sets.visited 1801) (.both (Sets.visited 1802) (.both (Sets.visited 1803) (.both (Sets.visited 1804) (.both (Sets.visited 1805) (.both (Sets.visited 1806) (.both (Sets.visited 1807) (.both (Sets.visited 1808) (.both (Sets.visited 1809) (.both (Sets.visited 1810) (.both (Sets.visited 1811) (.both (Sets.visited 1812) (.both (Sets.visited 1813) (.both (Sets.visited 1814) (.both (Sets.visited 1815) (.both (Sets.visited 1816) (.both (Sets.visited 1817) (.both (Sets.visited 1818) (.both (Sets.visited 1819) (.both (Sets.visited 1820) (.both (Sets.visited 1821) (.both (Sets.visited 1822) (.both (Sets.visited 1823) (.both (Sets.visited 1824) (.both (Sets.visited 1825) (.both (Sets.visited 1826) (.both (Sets.visited 1827) (.both (Sets.visited 1828) (.both (Sets.visited 1829) (.both (Sets.visited 1830) (.both (Sets.visited 1831) (.both (Sets.visited 1832) (.both (Sets.visited 1833) (Sets.visited 1834)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M265

#print axioms Cert.M265.verified
