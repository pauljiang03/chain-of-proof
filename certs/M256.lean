import ChainOfProof
open ChainOfProof

namespace Cert.M256

def cited : List Fact := [
  ⟨1437, .programRun, 1427295290420205, 1, 1009, 1010⟩,
  ⟨1438, .programRun, 1427295438245805, 1, 1011, 1012⟩,
  ⟨1439, .programRun, 1427295438495405, 1, 910, 911⟩,
  ⟨1440, .programRun, 1427295476882000, 1, 964, 965⟩,
  ⟨1441, .programRun, 1427295476882005, 1, 1013, 1014⟩,
  ⟨1442, .programRun, 1427295514228405, 1, 1015, 0⟩,
  ⟨1443, .programRun, 1427295519048803, 1, 962, 963⟩,
  ⟨1444, .programRun, 1427295519048803, 1, 828, 833⟩,
  ⟨1445, .programRun, 1427295519048803, 1, 964, 965⟩,
  ⟨1446, .programRun, 1427295519048803, 1, 765, 889⟩,
  ⟨1447, .programRun, 1427295519048803, 1, 890, 891⟩,
  ⟨1448, .programRun, 1427296091101805, 1, 1016, 1017⟩,
  ⟨1449, .programRun, 1427296348735000, 1, 763, 1018⟩,
  ⟨1450, .programRun, 1427296348735000, 1, 1019, 1020⟩,
  ⟨1451, .programRun, 1427296410777005, 1, 1021, 1022⟩,
  ⟨1452, .programRun, 1427296485235805, 1, 1023, 1024⟩,
  ⟨1453, .programRun, 1427296550711000, 1, 1025, 1026⟩,
  ⟨1454, .programRun, 1427296550711000, 1, 773, 1027⟩,
  ⟨1455, .programRun, 1427296550711605, 1, 1028, 1029⟩,
  ⟨1456, .programRun, 1427296552256004, 1, 542, 1030⟩,
  ⟨1457, .programRun, 1427296552256004, 1, 542, 1031⟩,
  ⟨1458, .programRun, 1427296552256004, 1, 1032, 1033⟩,
  ⟨1459, .programRun, 1427296552256004, 1, 1034, 1035⟩,
  ⟨1460, .programRun, 1427296552256004, 1, 371, 1036⟩,
  ⟨1461, .programRun, 1427296552256004, 1, 373, 1037⟩,
  ⟨1462, .programRun, 1427296552256004, 1, 366, 1038⟩,
  ⟨1463, .programRun, 1427296552256004, 1, 366, 1039⟩,
  ⟨1464, .programRun, 1427296552256004, 1, 530, 1040⟩,
  ⟨1465, .programRun, 1427296552256004, 1, 530, 1041⟩,
  ⟨1466, .programRun, 1427296552256004, 1, 376, 1042⟩,
  ⟨1467, .programRun, 1427296552256004, 1, 532, 1043⟩,
  ⟨1468, .programRun, 1427296552256004, 1, 532, 1044⟩,
  ⟨1469, .programRun, 1427296552256004, 1, 1045, 1046⟩,
  ⟨1470, .programRun, 1427296552256004, 1, 1045, 1047⟩,
  ⟨1471, .programRun, 1427296552256004, 1, 707, 1048⟩,
  ⟨1472, .programRun, 1427296552256004, 1, 1049, 1050⟩,
  ⟨1473, .programRun, 1427296552256004, 1, 484, 1051⟩,
  ⟨1474, .programRun, 1427296552256004, 1, 484, 1052⟩,
  ⟨1475, .programRun, 1427296552256004, 1, 635, 1053⟩,
  ⟨1476, .programRun, 1427296552256004, 1, 595, 1054⟩ ]

def claim : Claim := .both (Sets.programRan 1437) (.both (Sets.programRan 1438) (.both (Sets.programRan 1439) (.both (Sets.programRan 1440) (.both (Sets.programRan 1441) (.both (Sets.programRan 1442) (.both (Sets.programRan 1443) (.both (Sets.programRan 1444) (.both (Sets.programRan 1445) (.both (Sets.programRan 1446) (.both (Sets.programRan 1447) (.both (Sets.programRan 1448) (.both (Sets.programRan 1449) (.both (Sets.programRan 1450) (.both (Sets.programRan 1451) (.both (Sets.programRan 1452) (.both (Sets.programRan 1453) (.both (Sets.programRan 1454) (.both (Sets.programRan 1455) (.both (Sets.programRan 1456) (.both (Sets.programRan 1457) (.both (Sets.programRan 1458) (.both (Sets.programRan 1459) (.both (Sets.programRan 1460) (.both (Sets.programRan 1461) (.both (Sets.programRan 1462) (.both (Sets.programRan 1463) (.both (Sets.programRan 1464) (.both (Sets.programRan 1465) (.both (Sets.programRan 1466) (.both (Sets.programRan 1467) (.both (Sets.programRan 1468) (.both (Sets.programRan 1469) (.both (Sets.programRan 1470) (.both (Sets.programRan 1471) (.both (Sets.programRan 1472) (.both (Sets.programRan 1473) (.both (Sets.programRan 1474) (.both (Sets.programRan 1475) (Sets.programRan 1476)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M256

#print axioms Cert.M256.verified
