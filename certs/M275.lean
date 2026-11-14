import ChainOfProof
open ChainOfProof

namespace Cert.M275

def cited : List Fact := [
  ⟨2195, .webVisit, 1427294820324305, 1, 1379, 1095⟩,
  ⟨2196, .webVisit, 1427294820905905, 1, 1380, 1095⟩,
  ⟨2197, .webVisit, 1427294821024505, 1, 1381, 1095⟩,
  ⟨2198, .webVisit, 1427294824631605, 1, 1382, 1095⟩,
  ⟨2199, .webVisit, 1427294824740805, 1, 1383, 1095⟩,
  ⟨2200, .webVisit, 1427294824818805, 1, 1384, 1095⟩,
  ⟨2201, .webVisit, 1427294824990405, 1, 1385, 1095⟩,
  ⟨2202, .webVisit, 1427294825361805, 1, 1386, 1095⟩,
  ⟨2203, .webVisit, 1427294825646805, 1, 1387, 1095⟩,
  ⟨2204, .webVisit, 1427294825649305, 1, 1387, 1095⟩,
  ⟨2205, .webVisit, 1427294825844000, 1, 1388, 1095⟩,
  ⟨2206, .webVisit, 1427294825844005, 1, 1388, 1095⟩,
  ⟨2207, .webVisit, 1427294825844005, 1, 1388, 1095⟩,
  ⟨2208, .webVisit, 1427294848053305, 1, 1389, 1095⟩,
  ⟨2209, .webVisit, 1427294848365305, 1, 1390, 1095⟩,
  ⟨2210, .webVisit, 1427294849085405, 1, 1391, 1095⟩,
  ⟨2211, .webVisit, 1427294849147805, 1, 1392, 1095⟩,
  ⟨2212, .webVisit, 1427294849709405, 1, 1393, 1095⟩,
  ⟨2213, .webVisit, 1427294849849000, 1, 1394, 1095⟩,
  ⟨2214, .webVisit, 1427294849849805, 1, 1394, 1095⟩,
  ⟨2215, .webVisit, 1427294849849805, 1, 1394, 1095⟩,
  ⟨2216, .webVisit, 1427294849857305, 1, 1395, 1095⟩,
  ⟨2217, .webVisit, 1427294850047705, 1, 1376, 1095⟩,
  ⟨2218, .webVisit, 1427294850047705, 1, 1388, 1095⟩,
  ⟨2219, .webVisit, 1427294854774505, 1, 1396, 1095⟩,
  ⟨2220, .webVisit, 1427294854774505, 1, 1396, 1095⟩,
  ⟨2221, .webVisit, 1427294854790105, 1, 1394, 1095⟩,
  ⟨2222, .webVisit, 1427294871248205, 1, 1397, 1095⟩,
  ⟨2223, .webVisit, 1427294872073505, 1, 1398, 1095⟩,
  ⟨2224, .webVisit, 1427294872073505, 1, 1399, 1095⟩,
  ⟨2225, .webVisit, 1427294872167105, 1, 1400, 1095⟩,
  ⟨2226, .webVisit, 1427294875942305, 1, 1401, 1095⟩,
  ⟨2227, .webVisit, 1427294875957000, 1, 1401, 1095⟩,
  ⟨2228, .webVisit, 1427294875957905, 1, 1401, 1095⟩,
  ⟨2229, .webVisit, 1427294892400905, 1, 1402, 1095⟩,
  ⟨2230, .webVisit, 1427294892400905, 1, 1402, 1095⟩,
  ⟨2231, .webVisit, 1427294892400905, 1, 1402, 1095⟩,
  ⟨2232, .webVisit, 1427294901830805, 1, 1403, 1095⟩,
  ⟨2233, .webVisit, 1427294902751205, 1, 1404, 1095⟩,
  ⟨2234, .webVisit, 1427294902751205, 1, 1404, 1095⟩ ]

def claim : Claim := .both (Sets.visited 2195) (.both (Sets.visited 2196) (.both (Sets.visited 2197) (.both (Sets.visited 2198) (.both (Sets.visited 2199) (.both (Sets.visited 2200) (.both (Sets.visited 2201) (.both (Sets.visited 2202) (.both (Sets.visited 2203) (.both (Sets.visited 2204) (.both (Sets.visited 2205) (.both (Sets.visited 2206) (.both (Sets.visited 2207) (.both (Sets.visited 2208) (.both (Sets.visited 2209) (.both (Sets.visited 2210) (.both (Sets.visited 2211) (.both (Sets.visited 2212) (.both (Sets.visited 2213) (.both (Sets.visited 2214) (.both (Sets.visited 2215) (.both (Sets.visited 2216) (.both (Sets.visited 2217) (.both (Sets.visited 2218) (.both (Sets.visited 2219) (.both (Sets.visited 2220) (.both (Sets.visited 2221) (.both (Sets.visited 2222) (.both (Sets.visited 2223) (.both (Sets.visited 2224) (.both (Sets.visited 2225) (.both (Sets.visited 2226) (.both (Sets.visited 2227) (.both (Sets.visited 2228) (.both (Sets.visited 2229) (.both (Sets.visited 2230) (.both (Sets.visited 2231) (.both (Sets.visited 2232) (.both (Sets.visited 2233) (Sets.visited 2234)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M275

#print axioms Cert.M275.verified
