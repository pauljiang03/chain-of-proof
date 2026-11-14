import ChainOfProof
open ChainOfProof

namespace Cert.M257

def cited : List Fact := [
  ⟨1477, .programRun, 1427296555610005, 1, 1055, 1056⟩,
  ⟨1478, .programRun, 1427296560196405, 1, 840, 845⟩,
  ⟨1479, .programRun, 1427296560196405, 1, 1057, 1058⟩,
  ⟨1480, .programRun, 1427296560321000, 1000, 840, 845⟩,
  ⟨1481, .programRun, 1427296560321205, 1, 840, 845⟩,
  ⟨1482, .programRun, 1427296560336000, 1000, 840, 845⟩,
  ⟨1483, .programRun, 1427296560336805, 1, 1059, 1060⟩,
  ⟨1484, .programRun, 1427296682328805, 1, 906, 1061⟩,
  ⟨1485, .programRun, 1427296709152405, 1, 1062, 1063⟩,
  ⟨1486, .programRun, 1427296709526805, 1, 906, 907⟩,
  ⟨1487, .programRun, 1427296709573605, 1, 906, 907⟩,
  ⟨1488, .programRun, 1427296709636005, 1, 1064, 1065⟩,
  ⟨1489, .programRun, 1427296709776405, 1, 1066, 1067⟩,
  ⟨1490, .programRun, 1427296716500005, 1, 1068, 1069⟩,
  ⟨1491, .programRun, 1427296717186405, 1, 1070, 1071⟩,
  ⟨1492, .programRun, 1427296734221605, 1, 1072, 1073⟩,
  ⟨1493, .programRun, 1427296751546205, 1, 1072, 1074⟩,
  ⟨1494, .programRun, 1427296890604000, 1, 1075, 1076⟩,
  ⟨1495, .programRun, 1427296890604000, 1, 765, 1077⟩,
  ⟨1496, .programRun, 1427296891899405, 1, 1078, 1079⟩,
  ⟨1497, .programRun, 1427296926874605, 1, 749, 1080⟩,
  ⟨1498, .programRun, 1427296927405005, 1, 749, 1081⟩,
  ⟨1499, .programRun, 1427297088177000, 1, 743, 1082⟩,
  ⟨1500, .programRun, 1427297088193205, 1, 743, 1083⟩,
  ⟨1501, .programRun, 1427297090127605, 1, 719, 1084⟩,
  ⟨1502, .programRun, 1427297093575205, 1, 906, 907⟩,
  ⟨1503, .programRun, 1427297313647604, 1, 743, 0⟩,
  ⟨1504, .programRun, 1427297313647604, 1, 668, 0⟩,
  ⟨1505, .programRun, 1427297313647604, 1, 1085, 0⟩,
  ⟨1506, .programRun, 1427297314022005, 1, 906, 907⟩,
  ⟨1507, .programRun, 1427297314552405, 1, 1086, 1087⟩,
  ⟨1508, .programRun, 1427297314568005, 1, 1088, 1089⟩,
  ⟨1509, .programRun, 1427297327126000, 1, 500, 1090⟩,
  ⟨1510, .programRun, 1427297327126005, 1, 1091, 1092⟩,
  ⟨1511, .programRun, 1427297352257605, 1, 828, 833⟩,
  ⟨1512, .programRun, 1427297352257605, 1, 698, 699⟩,
  ⟨1513, .programRun, 1427297352257605, 1, 668, 669⟩,
  ⟨1514, .programRun, 1427297352257605, 1, 500, 1093⟩ ]

def claim : Claim := .both (Sets.programRan 1477) (.both (Sets.programRan 1478) (.both (Sets.programRan 1479) (.both (Sets.programRan 1480) (.both (Sets.programRan 1481) (.both (Sets.programRan 1482) (.both (Sets.programRan 1483) (.both (Sets.programRan 1484) (.both (Sets.programRan 1485) (.both (Sets.programRan 1486) (.both (Sets.programRan 1487) (.both (Sets.programRan 1488) (.both (Sets.programRan 1489) (.both (Sets.programRan 1490) (.both (Sets.programRan 1491) (.both (Sets.programRan 1492) (.both (Sets.programRan 1493) (.both (Sets.programRan 1494) (.both (Sets.programRan 1495) (.both (Sets.programRan 1496) (.both (Sets.programRan 1497) (.both (Sets.programRan 1498) (.both (Sets.programRan 1499) (.both (Sets.programRan 1500) (.both (Sets.programRan 1501) (.both (Sets.programRan 1502) (.both (Sets.programRan 1503) (.both (Sets.programRan 1504) (.both (Sets.programRan 1505) (.both (Sets.programRan 1506) (.both (Sets.programRan 1507) (.both (Sets.programRan 1508) (.both (Sets.programRan 1509) (.both (Sets.programRan 1510) (.both (Sets.programRan 1511) (.both (Sets.programRan 1512) (.both (Sets.programRan 1513) (Sets.programRan 1514)))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M257

#print axioms Cert.M257.verified
