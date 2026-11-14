import ChainOfProof
open ChainOfProof

namespace Cert.M255

def cited : List Fact := [
  ⟨1397, .programRun, 1427294463667000, 1, 947, 948⟩,
  ⟨1398, .programRun, 1427294463667805, 1, 739, 949⟩,
  ⟨1399, .programRun, 1427294567891000, 1, 950, 0⟩,
  ⟨1400, .programRun, 1427294567891000, 1, 951, 952⟩,
  ⟨1401, .programRun, 1427294567891405, 1, 953, 954⟩,
  ⟨1402, .programRun, 1427294568125405, 1, 955, 956⟩,
  ⟨1403, .programRun, 1427294700148205, 1, 957, 958⟩,
  ⟨1404, .programRun, 1427294765975000, 1, 959, 960⟩,
  ⟨1405, .programRun, 1427294765975000, 1, 961, 0⟩,
  ⟨1406, .programRun, 1427294860265705, 1, 962, 963⟩,
  ⟨1407, .programRun, 1427294908867805, 1, 964, 965⟩,
  ⟨1408, .programRun, 1427295014393000, 1, 962, 963⟩,
  ⟨1409, .programRun, 1427295014393805, 1, 966, 967⟩,
  ⟨1410, .programRun, 1427295015579405, 1, 968, 969⟩,
  ⟨1411, .programRun, 1427295015657405, 1, 970, 971⟩,
  ⟨1412, .programRun, 1427295017389005, 1, 717, 972⟩,
  ⟨1413, .programRun, 1427295026905005, 1, 973, 974⟩,
  ⟨1414, .programRun, 1427295028948605, 1, 975, 976⟩,
  ⟨1415, .programRun, 1427295039400605, 1, 977, 0⟩,
  ⟨1416, .programRun, 1427295039743805, 1, 978, 979⟩,
  ⟨1417, .programRun, 1427295053066205, 1, 980, 981⟩,
  ⟨1418, .programRun, 1427295101426205, 1, 982, 983⟩,
  ⟨1419, .programRun, 1427295101473005, 1, 982, 984⟩,
  ⟨1420, .programRun, 1427295195806205, 1, 927, 985⟩,
  ⟨1421, .programRun, 1427295241826205, 1, 986, 987⟩,
  ⟨1422, .programRun, 1427295241919805, 1, 986, 988⟩,
  ⟨1423, .programRun, 1427295247099005, 1, 989, 990⟩,
  ⟨1424, .programRun, 1427295247629405, 1, 991, 992⟩,
  ⟨1425, .programRun, 1427295249189405, 1, 989, 993⟩,
  ⟨1426, .programRun, 1427295249595005, 1, 994, 995⟩,
  ⟨1427, .programRun, 1427295249657405, 1, 994, 996⟩,
  ⟨1428, .programRun, 1427295261357405, 1, 997, 998⟩,
  ⟨1429, .programRun, 1427295263011005, 1, 999, 1000⟩,
  ⟨1430, .programRun, 1427295268767405, 1, 997, 0⟩,
  ⟨1431, .programRun, 1427295269141805, 1, 999, 1001⟩,
  ⟨1432, .programRun, 1427295279079005, 1, 1002, 1003⟩,
  ⟨1433, .programRun, 1427295279734205, 1, 927, 1004⟩,
  ⟨1434, .programRun, 1427295282417405, 1, 1002, 1005⟩,
  ⟨1435, .programRun, 1427295288953805, 1, 1006, 1007⟩,
  ⟨1436, .programRun, 1427295289187805, 1, 1006, 1008⟩ ]

def claim : Claim := .both (Sets.programRan 1397) (.both (Sets.programRan 1398) (.both (Sets.programRan 1399) (.both (Sets.programRan 1400) (.both (Sets.programRan 1401) (.both (Sets.programRan 1402) (.both (Sets.programRan 1403) (.both (Sets.programRan 1404) (.both (Sets.programRan 1405) (.both (Sets.programRan 1406) (.both (Sets.programRan 1407) (.both (Sets.programRan 1408) (.both (Sets.programRan 1409) (.both (Sets.programRan 1410) (.both (Sets.programRan 1411) (.both (Sets.programRan 1412) (.both (Sets.programRan 1413) (.both (Sets.programRan 1414) (.both (Sets.programRan 1415) (.both (Sets.programRan 1416) (.both (Sets.programRan 1417) (.both (Sets.programRan 1418) (.both (Sets.programRan 1419) (.both (Sets.programRan 1420) (.both (Sets.programRan 1421) (.both (Sets.programRan 1422) (.both (Sets.programRan 1423) (.both (Sets.programRan 1424) (.both (Sets.programRan 1425) (.both (Sets.programRan 1426) (.both (Sets.programRan 1427) (.both (Sets.programRan 1428) (.both (Sets.programRan 1429) (.both (Sets.programRan 1430) (.both (Sets.programRan 1431) (.both (Sets.programRan 1432) (.both (Sets.programRan 1433) (.both (Sets.programRan 1434) (.both (Sets.programRan 1435) (Sets.programRan 1436)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M255

#print axioms Cert.M255.verified
