import ChainOfProof
open ChainOfProof

namespace Cert.M271

def cited : List Fact := [
  ⟨2035, .webVisit, 1427144026658465, 1, 1311, 1095⟩,
  ⟨2036, .webVisit, 1427144028550967, 1, 1312, 1095⟩,
  ⟨2037, .webVisit, 1427144108521000, 1, 1313, 1095⟩,
  ⟨2038, .webVisit, 1427144108521079, 1, 1313, 1095⟩,
  ⟨2039, .webVisit, 1427144108521079, 1, 1313, 1095⟩,
  ⟨2040, .webVisit, 1427144108553580, 1, 1313, 1095⟩,
  ⟨2041, .webVisit, 1427144110333085, 1, 1314, 1095⟩,
  ⟨2042, .webVisit, 1427144110333085, 1, 1314, 1095⟩,
  ⟨2043, .webVisit, 1427144110333085, 1, 1314, 1095⟩,
  ⟨2044, .webVisit, 1427144110353085, 1, 1314, 1095⟩,
  ⟨2045, .webVisit, 1427144112365588, 1, 1315, 1095⟩,
  ⟨2046, .webVisit, 1427144117465000, 1, 1316, 1095⟩,
  ⟨2047, .webVisit, 1427144117465595, 1, 1316, 1095⟩,
  ⟨2048, .webVisit, 1427144117465595, 1, 1316, 1095⟩,
  ⟨2049, .webVisit, 1427144117475595, 1, 1316, 1095⟩,
  ⟨2050, .webVisit, 1427144118330000, 1, 1317, 1095⟩,
  ⟨2051, .webVisit, 1427144118330597, 1, 1317, 1095⟩,
  ⟨2052, .webVisit, 1427144118330597, 1, 1317, 1095⟩,
  ⟨2053, .webVisit, 1427144118340597, 1, 1317, 1095⟩,
  ⟨2054, .webVisit, 1427144120480600, 1, 1318, 1095⟩,
  ⟨2055, .webVisit, 1427144129240000, 1, 1319, 1095⟩,
  ⟨2056, .webVisit, 1427144129240612, 1, 1319, 1095⟩,
  ⟨2057, .webVisit, 1427144129240612, 1, 1319, 1095⟩,
  ⟨2058, .webVisit, 1427144129265612, 1, 1319, 1095⟩,
  ⟨2059, .webVisit, 1427144131035615, 1, 1320, 1095⟩,
  ⟨2060, .webVisit, 1427144154787000, 1, 1321, 1095⟩,
  ⟨2061, .webVisit, 1427144154787650, 1, 1321, 1095⟩,
  ⟨2062, .webVisit, 1427144154787650, 1, 1321, 1095⟩,
  ⟨2063, .webVisit, 1427144154827650, 1, 1321, 1095⟩,
  ⟨2064, .webVisit, 1427144156134000, 1, 1322, 1095⟩,
  ⟨2065, .webVisit, 1427144156134654, 1, 1322, 1095⟩,
  ⟨2066, .webVisit, 1427144156134654, 1, 1322, 1095⟩,
  ⟨2067, .webVisit, 1427144156154654, 1, 1322, 1095⟩,
  ⟨2068, .webVisit, 1427144157412000, 1, 1323, 1095⟩,
  ⟨2069, .webVisit, 1427144157412156, 1, 1323, 1095⟩,
  ⟨2070, .webVisit, 1427144157412156, 1, 1323, 1095⟩,
  ⟨2071, .webVisit, 1427144157439656, 1, 1323, 1095⟩,
  ⟨2072, .webVisit, 1427144158732158, 1, 1324, 1095⟩,
  ⟨2073, .webVisit, 1427144158742000, 1, 1324, 1095⟩,
  ⟨2074, .webVisit, 1427144158742158, 1, 1324, 1095⟩ ]

def claim : Claim := .both (Sets.visited 2035) (.both (Sets.visited 2036) (.both (Sets.visited 2037) (.both (Sets.visited 2038) (.both (Sets.visited 2039) (.both (Sets.visited 2040) (.both (Sets.visited 2041) (.both (Sets.visited 2042) (.both (Sets.visited 2043) (.both (Sets.visited 2044) (.both (Sets.visited 2045) (.both (Sets.visited 2046) (.both (Sets.visited 2047) (.both (Sets.visited 2048) (.both (Sets.visited 2049) (.both (Sets.visited 2050) (.both (Sets.visited 2051) (.both (Sets.visited 2052) (.both (Sets.visited 2053) (.both (Sets.visited 2054) (.both (Sets.visited 2055) (.both (Sets.visited 2056) (.both (Sets.visited 2057) (.both (Sets.visited 2058) (.both (Sets.visited 2059) (.both (Sets.visited 2060) (.both (Sets.visited 2061) (.both (Sets.visited 2062) (.both (Sets.visited 2063) (.both (Sets.visited 2064) (.both (Sets.visited 2065) (.both (Sets.visited 2066) (.both (Sets.visited 2067) (.both (Sets.visited 2068) (.both (Sets.visited 2069) (.both (Sets.visited 2070) (.both (Sets.visited 2071) (.both (Sets.visited 2072) (.both (Sets.visited 2073) (Sets.visited 2074)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M271

#print axioms Cert.M271.verified
