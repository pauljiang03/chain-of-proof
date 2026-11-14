import ChainOfProof
open ChainOfProof

namespace Cert.M266

def cited : List Fact := [
  ⟨1835, .webVisit, 1427134438382908, 1, 1207, 1095⟩,
  ⟨1836, .webVisit, 1427134438392908, 1, 1164, 1095⟩,
  ⟨1837, .webVisit, 1427134451977428, 1, 1208, 1095⟩,
  ⟨1838, .webVisit, 1427134453432433, 1, 1209, 1095⟩,
  ⟨1839, .webVisit, 1427134453442433, 1, 1209, 1095⟩,
  ⟨1840, .webVisit, 1427134464642450, 1, 1210, 1095⟩,
  ⟨1841, .webVisit, 1427134464652000, 1, 1210, 1095⟩,
  ⟨1842, .webVisit, 1427134464652450, 1, 1210, 1095⟩,
  ⟨1843, .webVisit, 1427134464822450, 1, 1211, 1095⟩,
  ⟨1844, .webVisit, 1427134471582459, 1, 1210, 1095⟩,
  ⟨1845, .webVisit, 1427134490369135, 1, 1212, 881⟩,
  ⟨1846, .webVisit, 1427134490369135, 1, 1212, 881⟩,
  ⟨1847, .webVisit, 1427134509349197, 1, 1213, 881⟩,
  ⟨1848, .webVisit, 1427134509349197, 1, 1213, 881⟩,
  ⟨1849, .webVisit, 1427134509567531, 1, 1214, 881⟩,
  ⟨1850, .webVisit, 1427134509567531, 1, 1214, 881⟩,
  ⟨1851, .webVisit, 1427134531663466, 1, 1215, 881⟩,
  ⟨1852, .webVisit, 1427134531663466, 1, 1215, 881⟩,
  ⟨1853, .webVisit, 1427134532142726, 1, 1216, 881⟩,
  ⟨1854, .webVisit, 1427134532142726, 1, 1216, 881⟩,
  ⟨1855, .webVisit, 1427134544517539, 1, 1217, 881⟩,
  ⟨1856, .webVisit, 1427134544517539, 1, 1217, 881⟩,
  ⟨1857, .webVisit, 1427134549629110, 1, 1218, 881⟩,
  ⟨1858, .webVisit, 1427134549629110, 1, 1218, 881⟩,
  ⟨1859, .webVisit, 1427134549823694, 1, 1219, 881⟩,
  ⟨1860, .webVisit, 1427134549823694, 1, 1219, 881⟩,
  ⟨1861, .webVisit, 1427134565664344, 1, 1220, 881⟩,
  ⟨1862, .webVisit, 1427134565664344, 1, 1220, 881⟩,
  ⟨1863, .webVisit, 1427134566580319, 1, 1221, 881⟩,
  ⟨1864, .webVisit, 1427134566580319, 1, 1221, 881⟩,
  ⟨1865, .webVisit, 1427134594730930, 1, 1222, 881⟩,
  ⟨1866, .webVisit, 1427134594730930, 1, 1222, 881⟩,
  ⟨1867, .webVisit, 1427134597429853, 1, 1221, 881⟩,
  ⟨1868, .webVisit, 1427134597429853, 1, 1221, 881⟩,
  ⟨1869, .webVisit, 1427134602973992, 1, 1223, 881⟩,
  ⟨1870, .webVisit, 1427134602973992, 1, 1223, 881⟩,
  ⟨1871, .webVisit, 1427134615783076, 1, 1224, 881⟩,
  ⟨1872, .webVisit, 1427134615783076, 1, 1224, 881⟩,
  ⟨1873, .webVisit, 1427134634631106, 1, 1225, 881⟩,
  ⟨1874, .webVisit, 1427134634631106, 1, 1225, 881⟩ ]

def claim : Claim := .both (Sets.visited 1835) (.both (Sets.visited 1836) (.both (Sets.visited 1837) (.both (Sets.visited 1838) (.both (Sets.visited 1839) (.both (Sets.visited 1840) (.both (Sets.visited 1841) (.both (Sets.visited 1842) (.both (Sets.visited 1843) (.both (Sets.visited 1844) (.both (Sets.visited 1845) (.both (Sets.visited 1846) (.both (Sets.visited 1847) (.both (Sets.visited 1848) (.both (Sets.visited 1849) (.both (Sets.visited 1850) (.both (Sets.visited 1851) (.both (Sets.visited 1852) (.both (Sets.visited 1853) (.both (Sets.visited 1854) (.both (Sets.visited 1855) (.both (Sets.visited 1856) (.both (Sets.visited 1857) (.both (Sets.visited 1858) (.both (Sets.visited 1859) (.both (Sets.visited 1860) (.both (Sets.visited 1861) (.both (Sets.visited 1862) (.both (Sets.visited 1863) (.both (Sets.visited 1864) (.both (Sets.visited 1865) (.both (Sets.visited 1866) (.both (Sets.visited 1867) (.both (Sets.visited 1868) (.both (Sets.visited 1869) (.both (Sets.visited 1870) (.both (Sets.visited 1871) (.both (Sets.visited 1872) (.both (Sets.visited 1873) (Sets.visited 1874)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M266

#print axioms Cert.M266.verified
