import ChainOfProof
open ChainOfProof

namespace Cert.M282

def cited : List Fact := [
  ⟨2351, .folderOpened, 1427039831064611, 1, 1455, 1434⟩,
  ⟨2352, .folderOpened, 1427039832413414, 1, 1454, 1434⟩,
  ⟨2353, .folderOpened, 1427039832413414, 1, 1462, 1434⟩,
  ⟨2354, .folderOpened, 1427039834951820, 1, 1462, 1434⟩,
  ⟨2355, .folderOpened, 1427039834951820, 1, 1463, 1434⟩,
  ⟨2356, .folderOpened, 1427039838087626, 1, 1463, 1434⟩,
  ⟨2357, .folderOpened, 1427039838087626, 1, 1464, 1434⟩,
  ⟨2358, .folderOpened, 1427039838087626, 1, 1455, 1434⟩,
  ⟨2359, .folderOpened, 1427039851020048, 1, 1465, 1466⟩,
  ⟨2360, .folderOpened, 1427135771219534, 1, 1467, 1434⟩,
  ⟨2361, .folderOpened, 1427135874476000, 1, 1468, 1469⟩,
  ⟨2362, .folderOpened, 1427135903398000, 1, 1470, 1469⟩,
  ⟨2363, .folderOpened, 1427141134139299, 1, 1471, 1434⟩,
  ⟨2364, .folderOpened, 1427142208098017, 1, 26, 1472⟩,
  ⟨2365, .folderOpened, 1427142208144819, 1, 1473, 1434⟩,
  ⟨2366, .folderOpened, 1427142208144819, 1, 1474, 1434⟩,
  ⟨2367, .folderOpened, 1427142208144819, 1, 26, 1434⟩,
  ⟨2368, .folderOpened, 1427142241231876, 1, 1475, 1434⟩,
  ⟨2369, .folderOpened, 1427142241247477, 1, 1473, 1434⟩,
  ⟨2370, .folderOpened, 1427142241247477, 1, 1474, 1434⟩,
  ⟨2371, .folderOpened, 1427142241247477, 1, 26, 1434⟩,
  ⟨2372, .folderOpened, 1427142247010288, 1, 1475, 1434⟩,
  ⟨2373, .folderOpened, 1427142248457491, 1, 1476, 1434⟩,
  ⟨2374, .folderOpened, 1427142249485493, 1, 1476, 1434⟩,
  ⟨2375, .folderOpened, 1427142252943098, 1, 1477, 1434⟩,
  ⟨2376, .folderOpened, 1427142252989899, 1, 26, 1434⟩,
  ⟨2377, .folderOpened, 1427142252989899, 1, 1478, 1434⟩,
  ⟨2378, .folderOpened, 1427142254753101, 1, 1477, 1434⟩,
  ⟨2379, .folderOpened, 1427142255814304, 1, 1479, 1434⟩,
  ⟨2380, .folderOpened, 1427142256937506, 1, 1480, 1434⟩,
  ⟨2381, .folderOpened, 1427142258481909, 1, 1481, 1434⟩,
  ⟨2382, .folderOpened, 1427142259565514, 1, 1481, 1434⟩,
  ⟨2383, .folderOpened, 1427142260978315, 1, 1482, 1434⟩,
  ⟨2384, .folderOpened, 1427142262135517, 1, 1482, 1434⟩,
  ⟨2385, .folderOpened, 1427142267816330, 1, 1483, 1434⟩,
  ⟨2386, .folderOpened, 1427142269507532, 1, 1483, 1434⟩,
  ⟨2387, .folderOpened, 1427142273096739, 1, 1479, 1434⟩,
  ⟨2388, .folderOpened, 1427142275434944, 1, 1473, 1434⟩,
  ⟨2389, .folderOpened, 1427142275434944, 1, 1480, 1434⟩,
  ⟨2390, .folderOpened, 1427142364313705, 1, 26, 1484⟩ ]

def claim : Claim := .both (Sets.folderRecorded 2351) (.both (Sets.folderRecorded 2352) (.both (Sets.folderRecorded 2353) (.both (Sets.folderRecorded 2354) (.both (Sets.folderRecorded 2355) (.both (Sets.folderRecorded 2356) (.both (Sets.folderRecorded 2357) (.both (Sets.folderRecorded 2358) (.both (Sets.folderRecorded 2359) (.both (Sets.folderRecorded 2360) (.both (Sets.folderRecorded 2361) (.both (Sets.folderRecorded 2362) (.both (Sets.folderRecorded 2363) (.both (Sets.folderRecorded 2364) (.both (Sets.folderRecorded 2365) (.both (Sets.folderRecorded 2366) (.both (Sets.folderRecorded 2367) (.both (Sets.folderRecorded 2368) (.both (Sets.folderRecorded 2369) (.both (Sets.folderRecorded 2370) (.both (Sets.folderRecorded 2371) (.both (Sets.folderRecorded 2372) (.both (Sets.folderRecorded 2373) (.both (Sets.folderRecorded 2374) (.both (Sets.folderRecorded 2375) (.both (Sets.folderRecorded 2376) (.both (Sets.folderRecorded 2377) (.both (Sets.folderRecorded 2378) (.both (Sets.folderRecorded 2379) (.both (Sets.folderRecorded 2380) (.both (Sets.folderRecorded 2381) (.both (Sets.folderRecorded 2382) (.both (Sets.folderRecorded 2383) (.both (Sets.folderRecorded 2384) (.both (Sets.folderRecorded 2385) (.both (Sets.folderRecorded 2386) (.both (Sets.folderRecorded 2387) (.both (Sets.folderRecorded 2388) (.both (Sets.folderRecorded 2389) (Sets.folderRecorded 2390)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M282

#print axioms Cert.M282.verified
