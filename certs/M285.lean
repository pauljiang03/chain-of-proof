import ChainOfProof
open ChainOfProof

namespace Cert.M285

def cited : List Fact := [
  ⟨2471, .folderOpened, 1427230874336063, 1, 1541, 1466⟩,
  ⟨2472, .folderOpened, 1427230874336063, 1, 1542, 1466⟩,
  ⟨2473, .folderOpened, 1427230874336063, 1, 1543, 1466⟩,
  ⟨2474, .folderOpened, 1427230874336063, 1, 1420, 1466⟩,
  ⟨2475, .folderOpened, 1427292857975405, 1, 1544, 1434⟩,
  ⟨2476, .folderOpened, 1427296760750204, 1, 1435, 1434⟩,
  ⟨2477, .folderOpened, 1427296760750204, 1, 1545, 1434⟩,
  ⟨2478, .folderOpened, 1427296859763405, 1, 1546, 1434⟩,
  ⟨2479, .folderOpened, 1427296859763405, 1, 1471, 1434⟩,
  ⟨2480, .folderOpened, 1427297089628000, 1, 1547, 1469⟩,
  ⟨2481, .folderOpened, 1427297289857605, 1, 1453, 1434⟩,
  ⟨2482, .folderOpened, 1427297289857605, 1, 1523, 1434⟩,
  ⟨2483, .folderOpened, 1427297313647604, 1, 1548, 1549⟩,
  ⟨2484, .folderOpened, 1427297313647604, 1, 1548, 1549⟩,
  ⟨2485, .folderOpened, 1427297313647604, 1, 1442, 1549⟩,
  ⟨2486, .folderOpened, 1427297406592403, 1, 1455, 1434⟩,
  ⟨2487, .folderOpened, 1427297409057203, 1, 1454, 1434⟩,
  ⟨2488, .folderOpened, 1427297409057203, 1, 1455, 1434⟩ ]

def claim : Claim := .both (Sets.folderRecorded 2471) (.both (Sets.folderRecorded 2472) (.both (Sets.folderRecorded 2473) (.both (Sets.folderRecorded 2474) (.both (Sets.folderRecorded 2475) (.both (Sets.folderRecorded 2476) (.both (Sets.folderRecorded 2477) (.both (Sets.folderRecorded 2478) (.both (Sets.folderRecorded 2479) (.both (Sets.folderRecorded 2480) (.both (Sets.folderRecorded 2481) (.both (Sets.folderRecorded 2482) (.both (Sets.folderRecorded 2483) (.both (Sets.folderRecorded 2484) (.both (Sets.folderRecorded 2485) (.both (Sets.folderRecorded 2486) (.both (Sets.folderRecorded 2487) (Sets.folderRecorded 2488)))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M285

#print axioms Cert.M285.verified
