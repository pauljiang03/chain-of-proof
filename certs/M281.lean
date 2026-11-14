import ChainOfProof
open ChainOfProof

namespace Cert.M281

def cited : List Fact := [
  ⟨2311, .folderOpened, 1427035043758997, 1, 1433, 1434⟩,
  ⟨2312, .folderOpened, 1427035043758997, 1, 1435, 1434⟩,
  ⟨2313, .folderOpened, 1427035056771820, 1, 1436, 1434⟩,
  ⟨2314, .folderOpened, 1427035056771820, 1, 1437, 1434⟩,
  ⟨2315, .folderOpened, 1427035070327644, 1, 1438, 1434⟩,
  ⟨2316, .folderOpened, 1427035080576862, 1, 1439, 1434⟩,
  ⟨2317, .folderOpened, 1427035080576862, 1, 1440, 1434⟩,
  ⟨2318, .folderOpened, 1427036911094250, 1, 1441, 1434⟩,
  ⟨2319, .folderOpened, 1427036918785063, 1, 1442, 1434⟩,
  ⟨2320, .folderOpened, 1427036953978724, 1, 1443, 1434⟩,
  ⟨2321, .folderOpened, 1427037041459888, 1, 1444, 1434⟩,
  ⟨2322, .folderOpened, 1427037118679625, 1, 1445, 1434⟩,
  ⟨2323, .folderOpened, 1427039497978083, 1, 1446, 1434⟩,
  ⟨2324, .folderOpened, 1427039503917894, 1, 1447, 1434⟩,
  ⟨2325, .folderOpened, 1427039503917894, 1, 1448, 1434⟩,
  ⟨2326, .folderOpened, 1427039514664713, 1, 1449, 1434⟩,
  ⟨2327, .folderOpened, 1427039530903942, 1, 1450, 1434⟩,
  ⟨2328, .folderOpened, 1427039537944355, 1, 1451, 1434⟩,
  ⟨2329, .folderOpened, 1427039585658842, 1, 1448, 1434⟩,
  ⟨2330, .folderOpened, 1427039585658842, 1, 1452, 1434⟩,
  ⟨2331, .folderOpened, 1427039594175657, 1, 1452, 1434⟩,
  ⟨2332, .folderOpened, 1427039594175657, 1, 1451, 1434⟩,
  ⟨2333, .folderOpened, 1427039777330902, 1, 1453, 1434⟩,
  ⟨2334, .folderOpened, 1427039779663706, 1, 1454, 1434⟩,
  ⟨2335, .folderOpened, 1427039779663706, 1, 1455, 1434⟩,
  ⟨2336, .folderOpened, 1427039780953711, 1, 1454, 1434⟩,
  ⟨2337, .folderOpened, 1427039780953711, 1, 1456, 1434⟩,
  ⟨2338, .folderOpened, 1427039782158911, 1, 1456, 1434⟩,
  ⟨2339, .folderOpened, 1427039782158911, 1, 1457, 1434⟩,
  ⟨2340, .folderOpened, 1427039785906919, 1, 1457, 1434⟩,
  ⟨2341, .folderOpened, 1427039785906919, 1, 1458, 1434⟩,
  ⟨2342, .folderOpened, 1427039797260740, 1, 1433, 1434⟩,
  ⟨2343, .folderOpened, 1427039797260740, 1, 1459, 1434⟩,
  ⟨2344, .folderOpened, 1427039802325951, 1, 1459, 1434⟩,
  ⟨2345, .folderOpened, 1427039802325951, 1, 1460, 1434⟩,
  ⟨2346, .folderOpened, 1427039811380367, 1, 1433, 1434⟩,
  ⟨2347, .folderOpened, 1427039811380367, 1, 1460, 1434⟩,
  ⟨2348, .folderOpened, 1427039811380367, 1, 1461, 1434⟩,
  ⟨2349, .folderOpened, 1427039829734402, 1, 1453, 1434⟩,
  ⟨2350, .folderOpened, 1427039831064611, 1, 1454, 1434⟩ ]

def claim : Claim := .both (Sets.folderRecorded 2311) (.both (Sets.folderRecorded 2312) (.both (Sets.folderRecorded 2313) (.both (Sets.folderRecorded 2314) (.both (Sets.folderRecorded 2315) (.both (Sets.folderRecorded 2316) (.both (Sets.folderRecorded 2317) (.both (Sets.folderRecorded 2318) (.both (Sets.folderRecorded 2319) (.both (Sets.folderRecorded 2320) (.both (Sets.folderRecorded 2321) (.both (Sets.folderRecorded 2322) (.both (Sets.folderRecorded 2323) (.both (Sets.folderRecorded 2324) (.both (Sets.folderRecorded 2325) (.both (Sets.folderRecorded 2326) (.both (Sets.folderRecorded 2327) (.both (Sets.folderRecorded 2328) (.both (Sets.folderRecorded 2329) (.both (Sets.folderRecorded 2330) (.both (Sets.folderRecorded 2331) (.both (Sets.folderRecorded 2332) (.both (Sets.folderRecorded 2333) (.both (Sets.folderRecorded 2334) (.both (Sets.folderRecorded 2335) (.both (Sets.folderRecorded 2336) (.both (Sets.folderRecorded 2337) (.both (Sets.folderRecorded 2338) (.both (Sets.folderRecorded 2339) (.both (Sets.folderRecorded 2340) (.both (Sets.folderRecorded 2341) (.both (Sets.folderRecorded 2342) (.both (Sets.folderRecorded 2343) (.both (Sets.folderRecorded 2344) (.both (Sets.folderRecorded 2345) (.both (Sets.folderRecorded 2346) (.both (Sets.folderRecorded 2347) (.both (Sets.folderRecorded 2348) (.both (Sets.folderRecorded 2349) (Sets.folderRecorded 2350)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M281

#print axioms Cert.M281.verified
