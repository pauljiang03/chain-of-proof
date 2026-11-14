import ChainOfProof
open ChainOfProof

namespace Cert.M274

def cited : List Fact := [
  ⟨2155, .webVisit, 1427223680890928, 1, 1114, 881⟩,
  ⟨2156, .webVisit, 1427223680892995, 1, 1114, 881⟩,
  ⟨2157, .webVisit, 1427224192003000, 1, 1362, 1095⟩,
  ⟨2158, .webVisit, 1427224194390000, 1, 1241, 1095⟩,
  ⟨2159, .webVisit, 1427225584742000, 1, 1363, 1095⟩,
  ⟨2160, .webVisit, 1427225584742456, 1, 1363, 1095⟩,
  ⟨2161, .webVisit, 1427225585272000, 1, 1364, 1095⟩,
  ⟨2162, .webVisit, 1427225585272857, 1, 1364, 1095⟩,
  ⟨2163, .webVisit, 1427229858901000, 1, 1365, 1095⟩,
  ⟨2164, .webVisit, 1427229858901833, 1, 1365, 1095⟩,
  ⟨2165, .webVisit, 1427230870904000, 1, 1366, 1095⟩,
  ⟨2166, .webVisit, 1427230870904057, 1, 1366, 1095⟩,
  ⟨2167, .webVisit, 1427230872900000, 1, 1367, 1095⟩,
  ⟨2168, .webVisit, 1427230872900860, 1, 1367, 1095⟩,
  ⟨2169, .webVisit, 1427230874320000, 1, 1368, 1095⟩,
  ⟨2170, .webVisit, 1427230874320463, 1, 1368, 1095⟩,
  ⟨2171, .webVisit, 1427231140083679, 1, 1114, 881⟩,
  ⟨2172, .webVisit, 1427231140083679, 1, 1114, 881⟩,
  ⟨2173, .webVisit, 1427231140207823, 1, 1115, 881⟩,
  ⟨2174, .webVisit, 1427231140207823, 1, 1115, 881⟩,
  ⟨2175, .webVisit, 1427231210726427, 1, 1369, 881⟩,
  ⟨2176, .webVisit, 1427231210726427, 1, 1369, 881⟩,
  ⟨2177, .webVisit, 1427231239567843, 1, 1107, 881⟩,
  ⟨2178, .webVisit, 1427231239567843, 1, 1107, 881⟩,
  ⟨2179, .webVisit, 1427294473308000, 1, 1118, 1095⟩,
  ⟨2180, .webVisit, 1427294473308605, 1, 1118, 1095⟩,
  ⟨2181, .webVisit, 1427294767988405, 1, 1370, 1095⟩,
  ⟨2182, .webVisit, 1427294804752000, 1, 1371, 1095⟩,
  ⟨2183, .webVisit, 1427294804752905, 1, 1371, 1095⟩,
  ⟨2184, .webVisit, 1427294804752905, 1, 1371, 1095⟩,
  ⟨2185, .webVisit, 1427294804771005, 1, 1371, 1095⟩,
  ⟨2186, .webVisit, 1427294805194105, 1, 1372, 1095⟩,
  ⟨2187, .webVisit, 1427294814471205, 1, 1373, 1095⟩,
  ⟨2188, .webVisit, 1427294815519505, 1, 1374, 1095⟩,
  ⟨2189, .webVisit, 1427294819388305, 1, 1375, 1095⟩,
  ⟨2190, .webVisit, 1427294819528000, 1, 1376, 1095⟩,
  ⟨2191, .webVisit, 1427294819528705, 1, 1376, 1095⟩,
  ⟨2192, .webVisit, 1427294819528705, 1, 1376, 1095⟩,
  ⟨2193, .webVisit, 1427294820261905, 1, 1377, 1095⟩,
  ⟨2194, .webVisit, 1427294820324305, 1, 1378, 1095⟩ ]

def claim : Claim := .both (Sets.visited 2155) (.both (Sets.visited 2156) (.both (Sets.visited 2157) (.both (Sets.visited 2158) (.both (Sets.visited 2159) (.both (Sets.visited 2160) (.both (Sets.visited 2161) (.both (Sets.visited 2162) (.both (Sets.visited 2163) (.both (Sets.visited 2164) (.both (Sets.visited 2165) (.both (Sets.visited 2166) (.both (Sets.visited 2167) (.both (Sets.visited 2168) (.both (Sets.visited 2169) (.both (Sets.visited 2170) (.both (Sets.visited 2171) (.both (Sets.visited 2172) (.both (Sets.visited 2173) (.both (Sets.visited 2174) (.both (Sets.visited 2175) (.both (Sets.visited 2176) (.both (Sets.visited 2177) (.both (Sets.visited 2178) (.both (Sets.visited 2179) (.both (Sets.visited 2180) (.both (Sets.visited 2181) (.both (Sets.visited 2182) (.both (Sets.visited 2183) (.both (Sets.visited 2184) (.both (Sets.visited 2185) (.both (Sets.visited 2186) (.both (Sets.visited 2187) (.both (Sets.visited 2188) (.both (Sets.visited 2189) (.both (Sets.visited 2190) (.both (Sets.visited 2191) (.both (Sets.visited 2192) (.both (Sets.visited 2193) (Sets.visited 2194)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M274

#print axioms Cert.M274.verified
