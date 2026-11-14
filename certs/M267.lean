import ChainOfProof
open ChainOfProof

namespace Cert.M267

def cited : List Fact := [
  ⟨1875, .webVisit, 1427134639020034, 1, 1226, 881⟩,
  ⟨1876, .webVisit, 1427134639020034, 1, 1226, 881⟩,
  ⟨1877, .webVisit, 1427134639898079, 1, 1227, 881⟩,
  ⟨1878, .webVisit, 1427134639898079, 1, 1227, 881⟩,
  ⟨1879, .webVisit, 1427134677947290, 1, 1228, 881⟩,
  ⟨1880, .webVisit, 1427134677947290, 1, 1228, 881⟩,
  ⟨1881, .webVisit, 1427134680896293, 1, 1229, 881⟩,
  ⟨1882, .webVisit, 1427134680896293, 1, 1229, 881⟩,
  ⟨1883, .webVisit, 1427134690237438, 1, 1230, 881⟩,
  ⟨1884, .webVisit, 1427134690237438, 1, 1230, 881⟩,
  ⟨1885, .webVisit, 1427134695855272, 1, 1231, 881⟩,
  ⟨1886, .webVisit, 1427134695855272, 1, 1231, 881⟩,
  ⟨1887, .webVisit, 1427134710872764, 1, 1232, 881⟩,
  ⟨1888, .webVisit, 1427134710872764, 1, 1232, 881⟩,
  ⟨1889, .webVisit, 1427134723263902, 1, 1233, 881⟩,
  ⟨1890, .webVisit, 1427134723263902, 1, 1233, 881⟩,
  ⟨1891, .webVisit, 1427134726050679, 1, 1234, 881⟩,
  ⟨1892, .webVisit, 1427134726050679, 1, 1234, 881⟩,
  ⟨1893, .webVisit, 1427134743860450, 1, 1235, 881⟩,
  ⟨1894, .webVisit, 1427134743860450, 1, 1235, 881⟩,
  ⟨1895, .webVisit, 1427134757603029, 1, 1236, 881⟩,
  ⟨1896, .webVisit, 1427134757603029, 1, 1236, 881⟩,
  ⟨1897, .webVisit, 1427134757818103, 1, 1237, 881⟩,
  ⟨1898, .webVisit, 1427134757818103, 1, 1237, 881⟩,
  ⟨1899, .webVisit, 1427134761173918, 1, 1238, 881⟩,
  ⟨1900, .webVisit, 1427134761173918, 1, 1238, 881⟩,
  ⟨1901, .webVisit, 1427134761977755, 1, 1239, 881⟩,
  ⟨1902, .webVisit, 1427134761977755, 1, 1239, 881⟩,
  ⟨1903, .webVisit, 1427135840514000, 1, 1240, 1095⟩,
  ⟨1904, .webVisit, 1427135840514856, 1, 1240, 1095⟩,
  ⟨1905, .webVisit, 1427135878142122, 1, 1241, 1095⟩,
  ⟨1906, .webVisit, 1427135901230000, 1, 1242, 1095⟩,
  ⟨1907, .webVisit, 1427135901230163, 1, 1242, 1095⟩,
  ⟨1908, .webVisit, 1427140063009625, 1, 1235, 881⟩,
  ⟨1909, .webVisit, 1427140063009625, 1, 1235, 881⟩,
  ⟨1910, .webVisit, 1427140063073290, 1, 1115, 881⟩,
  ⟨1911, .webVisit, 1427140063073290, 1, 1115, 881⟩,
  ⟨1912, .webVisit, 1427140085964295, 1, 1107, 881⟩,
  ⟨1913, .webVisit, 1427140085964295, 1, 1107, 881⟩,
  ⟨1914, .webVisit, 1427140099531147, 1, 1243, 881⟩ ]

def claim : Claim := .both (Sets.visited 1875) (.both (Sets.visited 1876) (.both (Sets.visited 1877) (.both (Sets.visited 1878) (.both (Sets.visited 1879) (.both (Sets.visited 1880) (.both (Sets.visited 1881) (.both (Sets.visited 1882) (.both (Sets.visited 1883) (.both (Sets.visited 1884) (.both (Sets.visited 1885) (.both (Sets.visited 1886) (.both (Sets.visited 1887) (.both (Sets.visited 1888) (.both (Sets.visited 1889) (.both (Sets.visited 1890) (.both (Sets.visited 1891) (.both (Sets.visited 1892) (.both (Sets.visited 1893) (.both (Sets.visited 1894) (.both (Sets.visited 1895) (.both (Sets.visited 1896) (.both (Sets.visited 1897) (.both (Sets.visited 1898) (.both (Sets.visited 1899) (.both (Sets.visited 1900) (.both (Sets.visited 1901) (.both (Sets.visited 1902) (.both (Sets.visited 1903) (.both (Sets.visited 1904) (.both (Sets.visited 1905) (.both (Sets.visited 1906) (.both (Sets.visited 1907) (.both (Sets.visited 1908) (.both (Sets.visited 1909) (.both (Sets.visited 1910) (.both (Sets.visited 1911) (.both (Sets.visited 1912) (.both (Sets.visited 1913) (Sets.visited 1914)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M267

#print axioms Cert.M267.verified
