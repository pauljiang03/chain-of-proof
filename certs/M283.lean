import ChainOfProof
open ChainOfProof

namespace Cert.M283

def cited : List Fact := [
  ⟨2391, .folderOpened, 1427142364407305, 1, 26, 1485⟩,
  ⟨2392, .folderOpened, 1427142416078000, 1, 1486, 1469⟩,
  ⟨2393, .folderOpened, 1427142444092247, 1, 1487, 1434⟩,
  ⟨2394, .folderOpened, 1427142444092247, 1, 1488, 1434⟩,
  ⟨2395, .folderOpened, 1427142449630657, 1, 1488, 1434⟩,
  ⟨2396, .folderOpened, 1427142449630657, 1, 1489, 1434⟩,
  ⟨2397, .folderOpened, 1427142457248000, 1, 1490, 1469⟩,
  ⟨2398, .folderOpened, 1427142497754147, 1, 1478, 1434⟩,
  ⟨2399, .folderOpened, 1427142497754147, 1, 1479, 1434⟩,
  ⟨2400, .folderOpened, 1427142497769747, 1, 1478, 1434⟩,
  ⟨2401, .folderOpened, 1427142497769747, 1, 1479, 1434⟩,
  ⟨2402, .folderOpened, 1427143690057993, 1, 1454, 1434⟩,
  ⟨2403, .folderOpened, 1427204311111279, 1, 1491, 1434⟩,
  ⟨2404, .folderOpened, 1427204311111279, 1, 1492, 1434⟩,
  ⟨2405, .folderOpened, 1427204332159714, 1, 1492, 1434⟩,
  ⟨2406, .folderOpened, 1427204332159714, 1, 1493, 1434⟩,
  ⟨2407, .folderOpened, 1427204413644859, 1, 1494, 1434⟩,
  ⟨2408, .folderOpened, 1427204413644859, 1, 1495, 1434⟩,
  ⟨2409, .folderOpened, 1427204874156872, 1, 26, 1434⟩,
  ⟨2410, .folderOpened, 1427204874156872, 1, 1476, 1434⟩,
  ⟨2411, .folderOpened, 1427204879257280, 1, 1496, 1434⟩,
  ⟨2412, .folderOpened, 1427204914247744, 1, 1497, 1434⟩,
  ⟨2413, .folderOpened, 1427205050506792, 1, 1498, 1434⟩,
  ⟨2414, .folderOpened, 1427205053798397, 1, 1499, 1434⟩,
  ⟨2415, .folderOpened, 1427205083499252, 1, 1500, 1434⟩,
  ⟨2416, .folderOpened, 1427205093994871, 1, 1501, 1434⟩,
  ⟨2417, .folderOpened, 1427205111001705, 1, 1502, 1434⟩,
  ⟨2418, .folderOpened, 1427205125601536, 1, 1503, 1434⟩,
  ⟨2419, .folderOpened, 1427205125601536, 1, 1500, 1434⟩,
  ⟨2420, .folderOpened, 1427205127726938, 1, 1504, 1434⟩,
  ⟨2421, .folderOpened, 1427205157682602, 1, 1505, 1434⟩,
  ⟨2422, .folderOpened, 1427205254610796, 1, 1506, 1434⟩,
  ⟨2423, .folderOpened, 1427205318165319, 1, 1507, 1434⟩,
  ⟨2424, .folderOpened, 1427205460731613, 1, 1495, 1434⟩,
  ⟨2425, .folderOpened, 1427205460731613, 1, 1497, 1434⟩,
  ⟨2426, .folderOpened, 1427205619073307, 1, 1508, 1434⟩,
  ⟨2427, .folderOpened, 1427205619073307, 1, 1509, 1434⟩,
  ⟨2428, .folderOpened, 1427205671731800, 1, 1510, 1434⟩,
  ⟨2429, .folderOpened, 1427205674350805, 1, 1511, 1434⟩,
  ⟨2430, .folderOpened, 1427205675923208, 1, 1512, 1434⟩ ]

def claim : Claim := .both (Sets.folderRecorded 2391) (.both (Sets.folderRecorded 2392) (.both (Sets.folderRecorded 2393) (.both (Sets.folderRecorded 2394) (.both (Sets.folderRecorded 2395) (.both (Sets.folderRecorded 2396) (.both (Sets.folderRecorded 2397) (.both (Sets.folderRecorded 2398) (.both (Sets.folderRecorded 2399) (.both (Sets.folderRecorded 2400) (.both (Sets.folderRecorded 2401) (.both (Sets.folderRecorded 2402) (.both (Sets.folderRecorded 2403) (.both (Sets.folderRecorded 2404) (.both (Sets.folderRecorded 2405) (.both (Sets.folderRecorded 2406) (.both (Sets.folderRecorded 2407) (.both (Sets.folderRecorded 2408) (.both (Sets.folderRecorded 2409) (.both (Sets.folderRecorded 2410) (.both (Sets.folderRecorded 2411) (.both (Sets.folderRecorded 2412) (.both (Sets.folderRecorded 2413) (.both (Sets.folderRecorded 2414) (.both (Sets.folderRecorded 2415) (.both (Sets.folderRecorded 2416) (.both (Sets.folderRecorded 2417) (.both (Sets.folderRecorded 2418) (.both (Sets.folderRecorded 2419) (.both (Sets.folderRecorded 2420) (.both (Sets.folderRecorded 2421) (.both (Sets.folderRecorded 2422) (.both (Sets.folderRecorded 2423) (.both (Sets.folderRecorded 2424) (.both (Sets.folderRecorded 2425) (.both (Sets.folderRecorded 2426) (.both (Sets.folderRecorded 2427) (.both (Sets.folderRecorded 2428) (.both (Sets.folderRecorded 2429) (Sets.folderRecorded 2430)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M283

#print axioms Cert.M283.verified
