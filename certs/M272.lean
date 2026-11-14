import ChainOfProof
open ChainOfProof

namespace Cert.M272

def cited : List Fact := [
  ⟨2075, .webVisit, 1427144160677162, 1, 1325, 1095⟩,
  ⟨2076, .webVisit, 1427144168707000, 1, 1326, 1095⟩,
  ⟨2077, .webVisit, 1427144168707174, 1, 1326, 1095⟩,
  ⟨2078, .webVisit, 1427144168707174, 1, 1326, 1095⟩,
  ⟨2079, .webVisit, 1427144170572177, 1, 1327, 1095⟩,
  ⟨2080, .webVisit, 1427144189403713, 1, 1328, 1095⟩,
  ⟨2081, .webVisit, 1427144189546215, 1, 1329, 1095⟩,
  ⟨2082, .webVisit, 1427144189621216, 1, 1330, 1095⟩,
  ⟨2083, .webVisit, 1427144189693718, 1, 1331, 1095⟩,
  ⟨2084, .webVisit, 1427144191906758, 1, 1332, 1095⟩,
  ⟨2085, .webVisit, 1427144192855777, 1, 1333, 1095⟩,
  ⟨2086, .webVisit, 1427144192858000, 1, 1333, 1095⟩,
  ⟨2087, .webVisit, 1427144192858277, 1, 1333, 1095⟩,
  ⟨2088, .webVisit, 1427144192898277, 1, 1334, 1095⟩,
  ⟨2089, .webVisit, 1427144192963278, 1, 1333, 1095⟩,
  ⟨2090, .webVisit, 1427144252966427, 1, 1335, 1095⟩,
  ⟨2091, .webVisit, 1427144253518434, 1, 1336, 1095⟩,
  ⟨2092, .webVisit, 1427144278459051, 1, 1326, 1095⟩,
  ⟨2093, .webVisit, 1427144284153564, 1, 1337, 1095⟩,
  ⟨2094, .webVisit, 1427203707744000, 1, 1118, 1095⟩,
  ⟨2095, .webVisit, 1427204063737000, 1, 1338, 1095⟩,
  ⟨2096, .webVisit, 1427204063737242, 1, 1338, 1095⟩,
  ⟨2097, .webVisit, 1427205692336000, 1, 1339, 1095⟩,
  ⟨2098, .webVisit, 1427205692336640, 1, 1339, 1095⟩,
  ⟨2099, .webVisit, 1427205914439000, 1, 1337, 1095⟩,
  ⟨2100, .webVisit, 1427205915518744, 1, 1340, 1095⟩,
  ⟨2101, .webVisit, 1427205915603746, 1, 1341, 1095⟩,
  ⟨2102, .webVisit, 1427205920625358, 1, 1115, 881⟩,
  ⟨2103, .webVisit, 1427205920625358, 1, 1115, 881⟩,
  ⟨2104, .webVisit, 1427205920849384, 1, 1107, 881⟩,
  ⟨2105, .webVisit, 1427205920849384, 1, 1107, 881⟩,
  ⟨2106, .webVisit, 1427206342954698, 1, 1115, 881⟩,
  ⟨2107, .webVisit, 1427206342954698, 1, 1115, 881⟩,
  ⟨2108, .webVisit, 1427206342982727, 1, 1107, 881⟩,
  ⟨2109, .webVisit, 1427206342982727, 1, 1107, 881⟩,
  ⟨2110, .webVisit, 1427210524755374, 1, 1342, 881⟩,
  ⟨2111, .webVisit, 1427210524755374, 1, 1342, 881⟩,
  ⟨2112, .webVisit, 1427210566570409, 1, 1343, 881⟩,
  ⟨2113, .webVisit, 1427210566570409, 1, 1343, 881⟩,
  ⟨2114, .webVisit, 1427210596123574, 1, 1344, 881⟩ ]

def claim : Claim := .both (Sets.visited 2075) (.both (Sets.visited 2076) (.both (Sets.visited 2077) (.both (Sets.visited 2078) (.both (Sets.visited 2079) (.both (Sets.visited 2080) (.both (Sets.visited 2081) (.both (Sets.visited 2082) (.both (Sets.visited 2083) (.both (Sets.visited 2084) (.both (Sets.visited 2085) (.both (Sets.visited 2086) (.both (Sets.visited 2087) (.both (Sets.visited 2088) (.both (Sets.visited 2089) (.both (Sets.visited 2090) (.both (Sets.visited 2091) (.both (Sets.visited 2092) (.both (Sets.visited 2093) (.both (Sets.visited 2094) (.both (Sets.visited 2095) (.both (Sets.visited 2096) (.both (Sets.visited 2097) (.both (Sets.visited 2098) (.both (Sets.visited 2099) (.both (Sets.visited 2100) (.both (Sets.visited 2101) (.both (Sets.visited 2102) (.both (Sets.visited 2103) (.both (Sets.visited 2104) (.both (Sets.visited 2105) (.both (Sets.visited 2106) (.both (Sets.visited 2107) (.both (Sets.visited 2108) (.both (Sets.visited 2109) (.both (Sets.visited 2110) (.both (Sets.visited 2111) (.both (Sets.visited 2112) (.both (Sets.visited 2113) (Sets.visited 2114)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M272

#print axioms Cert.M272.verified
