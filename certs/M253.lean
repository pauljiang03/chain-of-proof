import ChainOfProof
open ChainOfProof

namespace Cert.M253

def cited : List Fact := [
  ⟨1317, .programRun, 1427039660274498, 1, 785, 786⟩,
  ⟨1318, .programRun, 1427039660274498, 1, 787, 788⟩,
  ⟨1319, .programRun, 1427039660274498, 1, 789, 0⟩,
  ⟨1320, .programRun, 1427039660274498, 1, 790, 0⟩,
  ⟨1321, .programRun, 1427039660274498, 1, 791, 0⟩,
  ⟨1322, .programRun, 1427039660274498, 1, 876, 0⟩,
  ⟨1323, .programRun, 1427039660274498, 1, 792, 793⟩,
  ⟨1324, .programRun, 1427039660274498, 1, 794, 795⟩,
  ⟨1325, .programRun, 1427039660274498, 1, 796, 797⟩,
  ⟨1326, .programRun, 1427039660274498, 1, 476, 798⟩,
  ⟨1327, .programRun, 1427039660274498, 1, 877, 878⟩,
  ⟨1328, .programRun, 1427039660274498, 1, 799, 800⟩,
  ⟨1329, .programRun, 1427039660274498, 1, 394, 801⟩,
  ⟨1330, .programRun, 1427039660274498, 1, 440, 802⟩,
  ⟨1331, .programRun, 1427039660274498, 1, 447, 803⟩,
  ⟨1332, .programRun, 1427039660274498, 1, 478, 804⟩,
  ⟨1333, .programRun, 1427039660274498, 1, 879, 880⟩,
  ⟨1334, .programRun, 1427039721552000, 1, 881, 0⟩,
  ⟨1335, .programRun, 1427039721552000, 1, 882, 883⟩,
  ⟨1336, .programRun, 1427039773259000, 1, 884, 885⟩,
  ⟨1337, .programRun, 1427039773259000, 1, 632, 886⟩,
  ⟨1338, .programRun, 1427039828314000, 1, 884, 885⟩,
  ⟨1339, .programRun, 1427039828314000, 1, 632, 886⟩,
  ⟨1340, .programRun, 1427039849834446, 1, 698, 699⟩,
  ⟨1341, .programRun, 1427039850942000, 1, 453, 887⟩,
  ⟨1342, .programRun, 1427131610084000, 1, 882, 883⟩,
  ⟨1343, .programRun, 1427140593481297, 1, 835, 888⟩,
  ⟨1344, .programRun, 1427140593481297, 1, 765, 889⟩,
  ⟨1345, .programRun, 1427140613339270, 1, 890, 891⟩,
  ⟨1346, .programRun, 1427140859996950, 1, 892, 893⟩,
  ⟨1347, .programRun, 1427140927567893, 1, 840, 894⟩,
  ⟨1348, .programRun, 1427140929627907, 1, 840, 895⟩,
  ⟨1349, .programRun, 1427141419749000, 1, 567, 896⟩,
  ⟨1350, .programRun, 1427142410677000, 1, 735, 897⟩,
  ⟨1351, .programRun, 1427142453220000, 1, 741, 898⟩,
  ⟨1352, .programRun, 1427205106483695, 1, 715, 716⟩,
  ⟨1353, .programRun, 1427206597941000, 1, 379, 899⟩,
  ⟨1354, .programRun, 1427221747178000, 1, 879, 880⟩,
  ⟨1355, .programRun, 1427221747209939, 1, 900, 901⟩,
  ⟨1356, .programRun, 1427221915797000, 1, 876, 0⟩ ]

def claim : Claim := .both (Sets.programRan 1317) (.both (Sets.programRan 1318) (.both (Sets.programRan 1319) (.both (Sets.programRan 1320) (.both (Sets.programRan 1321) (.both (Sets.programRan 1322) (.both (Sets.programRan 1323) (.both (Sets.programRan 1324) (.both (Sets.programRan 1325) (.both (Sets.programRan 1326) (.both (Sets.programRan 1327) (.both (Sets.programRan 1328) (.both (Sets.programRan 1329) (.both (Sets.programRan 1330) (.both (Sets.programRan 1331) (.both (Sets.programRan 1332) (.both (Sets.programRan 1333) (.both (Sets.programRan 1334) (.both (Sets.programRan 1335) (.both (Sets.programRan 1336) (.both (Sets.programRan 1337) (.both (Sets.programRan 1338) (.both (Sets.programRan 1339) (.both (Sets.programRan 1340) (.both (Sets.programRan 1341) (.both (Sets.programRan 1342) (.both (Sets.programRan 1343) (.both (Sets.programRan 1344) (.both (Sets.programRan 1345) (.both (Sets.programRan 1346) (.both (Sets.programRan 1347) (.both (Sets.programRan 1348) (.both (Sets.programRan 1349) (.both (Sets.programRan 1350) (.both (Sets.programRan 1351) (.both (Sets.programRan 1352) (.both (Sets.programRan 1353) (.both (Sets.programRan 1354) (.both (Sets.programRan 1355) (Sets.programRan 1356)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M253

#print axioms Cert.M253.verified
