import ChainOfProof
open ChainOfProof

namespace Cert.M284

def cited : List Fact := [
  ⟨2431, .folderOpened, 1427205677015610, 1, 1513, 1434⟩,
  ⟨2432, .folderOpened, 1427205689766235, 1, 1514, 1434⟩,
  ⟨2433, .folderOpened, 1427205689766235, 1, 1515, 1434⟩,
  ⟨2434, .folderOpened, 1427205692305439, 1, 1515, 1434⟩,
  ⟨2435, .folderOpened, 1427205692305439, 1, 1516, 1434⟩,
  ⟨2436, .folderOpened, 1427206593235535, 1, 1517, 1434⟩,
  ⟨2437, .folderOpened, 1427206593235535, 1, 1518, 1434⟩,
  ⟨2438, .folderOpened, 1427208247795061, 1, 1519, 1434⟩,
  ⟨2439, .folderOpened, 1427208261552691, 1, 1520, 1434⟩,
  ⟨2440, .folderOpened, 1427208262079493, 1, 1521, 1434⟩,
  ⟨2441, .folderOpened, 1427208263573296, 1, 1522, 1434⟩,
  ⟨2442, .folderOpened, 1427208263573296, 1, 1521, 1434⟩,
  ⟨2443, .folderOpened, 1427222878362682, 1, 1523, 1434⟩,
  ⟨2444, .folderOpened, 1427226727803488, 1, 1524, 1434⟩,
  ⟨2445, .folderOpened, 1427226733528696, 1, 1525, 1434⟩,
  ⟨2446, .folderOpened, 1427226769629368, 1, 1526, 1434⟩,
  ⟨2447, .folderOpened, 1427226769629368, 1, 1520, 1434⟩,
  ⟨2448, .folderOpened, 1427226776214180, 1, 1527, 1434⟩,
  ⟨2449, .folderOpened, 1427226776214180, 1, 1523, 1434⟩,
  ⟨2450, .folderOpened, 1427226777417986, 1, 1528, 1434⟩,
  ⟨2451, .folderOpened, 1427226778065187, 1, 1529, 1434⟩,
  ⟨2452, .folderOpened, 1427226778065187, 1, 1528, 1434⟩,
  ⟨2453, .folderOpened, 1427226875357359, 1, 1530, 1434⟩,
  ⟨2454, .folderOpened, 1427226883463776, 1, 1531, 1434⟩,
  ⟨2455, .folderOpened, 1427226883463776, 1, 1530, 1434⟩,
  ⟨2456, .folderOpened, 1427226883463776, 1, 1532, 1434⟩,
  ⟨2457, .folderOpened, 1427226885043379, 1, 1532, 1434⟩,
  ⟨2458, .folderOpened, 1427226885043379, 1, 1533, 1434⟩,
  ⟨2459, .folderOpened, 1427226886196581, 1, 1534, 1434⟩,
  ⟨2460, .folderOpened, 1427227314703939, 1, 1535, 1434⟩,
  ⟨2461, .folderOpened, 1427229850111809, 1, 1536, 1434⟩,
  ⟨2462, .folderOpened, 1427229851038210, 1, 1537, 1434⟩,
  ⟨2463, .folderOpened, 1427229851735014, 1, 1538, 1434⟩,
  ⟨2464, .folderOpened, 1427229853155819, 1, 1531, 1434⟩,
  ⟨2465, .folderOpened, 1427229853155819, 1, 1530, 1434⟩,
  ⟨2466, .folderOpened, 1427229858477831, 1, 1533, 1434⟩,
  ⟨2467, .folderOpened, 1427229858477831, 1, 1539, 1434⟩,
  ⟨2468, .folderOpened, 1427230447914675, 1, 1509, 1434⟩,
  ⟨2469, .folderOpened, 1427230447914675, 1, 1512, 1434⟩,
  ⟨2470, .folderOpened, 1427230874336063, 1, 1540, 1466⟩ ]

def claim : Claim := .both (Sets.folderRecorded 2431) (.both (Sets.folderRecorded 2432) (.both (Sets.folderRecorded 2433) (.both (Sets.folderRecorded 2434) (.both (Sets.folderRecorded 2435) (.both (Sets.folderRecorded 2436) (.both (Sets.folderRecorded 2437) (.both (Sets.folderRecorded 2438) (.both (Sets.folderRecorded 2439) (.both (Sets.folderRecorded 2440) (.both (Sets.folderRecorded 2441) (.both (Sets.folderRecorded 2442) (.both (Sets.folderRecorded 2443) (.both (Sets.folderRecorded 2444) (.both (Sets.folderRecorded 2445) (.both (Sets.folderRecorded 2446) (.both (Sets.folderRecorded 2447) (.both (Sets.folderRecorded 2448) (.both (Sets.folderRecorded 2449) (.both (Sets.folderRecorded 2450) (.both (Sets.folderRecorded 2451) (.both (Sets.folderRecorded 2452) (.both (Sets.folderRecorded 2453) (.both (Sets.folderRecorded 2454) (.both (Sets.folderRecorded 2455) (.both (Sets.folderRecorded 2456) (.both (Sets.folderRecorded 2457) (.both (Sets.folderRecorded 2458) (.both (Sets.folderRecorded 2459) (.both (Sets.folderRecorded 2460) (.both (Sets.folderRecorded 2461) (.both (Sets.folderRecorded 2462) (.both (Sets.folderRecorded 2463) (.both (Sets.folderRecorded 2464) (.both (Sets.folderRecorded 2465) (.both (Sets.folderRecorded 2466) (.both (Sets.folderRecorded 2467) (.both (Sets.folderRecorded 2468) (.both (Sets.folderRecorded 2469) (Sets.folderRecorded 2470)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M284

#print axioms Cert.M284.verified
