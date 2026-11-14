import ChainOfProof
open ChainOfProof

namespace Cert.M254

def cited : List Fact := [
  ⟨1357, .programRun, 1427221915797000, 1, 877, 878⟩,
  ⟨1358, .programRun, 1427221915797063, 1, 902, 903⟩,
  ⟨1359, .programRun, 1427221935640000, 1, 904, 905⟩,
  ⟨1360, .programRun, 1427228643518676, 1, 906, 907⟩,
  ⟨1361, .programRun, 1427230378026551, 1, 908, 909⟩,
  ⟨1362, .programRun, 1427230732193809, 1, 910, 911⟩,
  ⟨1363, .programRun, 1427230870592056, 1, 906, 907⟩,
  ⟨1364, .programRun, 1427230967567629, 1, 912, 913⟩,
  ⟨1365, .programRun, 1427230991981671, 1, 908, 909⟩,
  ⟨1366, .programRun, 1427231138180000, 1, 881, 0⟩,
  ⟨1367, .programRun, 1427231138180000, 1, 882, 914⟩,
  ⟨1368, .programRun, 1427231138872937, 1, 915, 916⟩,
  ⟨1369, .programRun, 1427278674837915, 1, 910, 911⟩,
  ⟨1370, .programRun, 1427278677708320, 1, 917, 918⟩,
  ⟨1371, .programRun, 1427278690547142, 1, 919, 920⟩,
  ⟨1372, .programRun, 1427278692029145, 1, 921, 922⟩,
  ⟨1373, .programRun, 1427278693464347, 1, 923, 924⟩,
  ⟨1374, .programRun, 1427278695414351, 1, 925, 926⟩,
  ⟨1375, .programRun, 1427278696724753, 1, 927, 928⟩,
  ⟨1376, .programRun, 1427278707348372, 1, 927, 929⟩,
  ⟨1377, .programRun, 1427279603067137, 1, 930, 931⟩,
  ⟨1378, .programRun, 1427288769184500, 1, 840, 845⟩,
  ⟨1379, .programRun, 1427288769371700, 1, 715, 716⟩,
  ⟨1380, .programRun, 1427288830175607, 1, 932, 0⟩,
  ⟨1381, .programRun, 1427288868582874, 1, 933, 934⟩,
  ⟨1382, .programRun, 1427288869222476, 1, 910, 911⟩,
  ⟨1383, .programRun, 1427288987782684, 1, 494, 935⟩,
  ⟨1384, .programRun, 1427289285587207, 1, 936, 0⟩,
  ⟨1385, .programRun, 1427289347113715, 1, 733, 937⟩,
  ⟨1386, .programRun, 1427289359999338, 1, 840, 845⟩,
  ⟨1387, .programRun, 1427289550194872, 1, 938, 939⟩,
  ⟨1388, .programRun, 1427289830605364, 1, 908, 909⟩,
  ⟨1389, .programRun, 1427290174383168, 1, 940, 941⟩,
  ⟨1390, .programRun, 1427290174398768, 1, 908, 909⟩,
  ⟨1391, .programRun, 1427290176925972, 1, 906, 907⟩,
  ⟨1392, .programRun, 1427293190817005, 1, 942, 943⟩,
  ⟨1393, .programRun, 1427293193625005, 1, 944, 945⟩,
  ⟨1394, .programRun, 1427293209568205, 1, 715, 716⟩,
  ⟨1395, .programRun, 1427293913299805, 1, 910, 911⟩,
  ⟨1396, .programRun, 1427294463667000, 1, 739, 946⟩ ]

def claim : Claim := .both (Sets.programRan 1357) (.both (Sets.programRan 1358) (.both (Sets.programRan 1359) (.both (Sets.programRan 1360) (.both (Sets.programRan 1361) (.both (Sets.programRan 1362) (.both (Sets.programRan 1363) (.both (Sets.programRan 1364) (.both (Sets.programRan 1365) (.both (Sets.programRan 1366) (.both (Sets.programRan 1367) (.both (Sets.programRan 1368) (.both (Sets.programRan 1369) (.both (Sets.programRan 1370) (.both (Sets.programRan 1371) (.both (Sets.programRan 1372) (.both (Sets.programRan 1373) (.both (Sets.programRan 1374) (.both (Sets.programRan 1375) (.both (Sets.programRan 1376) (.both (Sets.programRan 1377) (.both (Sets.programRan 1378) (.both (Sets.programRan 1379) (.both (Sets.programRan 1380) (.both (Sets.programRan 1381) (.both (Sets.programRan 1382) (.both (Sets.programRan 1383) (.both (Sets.programRan 1384) (.both (Sets.programRan 1385) (.both (Sets.programRan 1386) (.both (Sets.programRan 1387) (.both (Sets.programRan 1388) (.both (Sets.programRan 1389) (.both (Sets.programRan 1390) (.both (Sets.programRan 1391) (.both (Sets.programRan 1392) (.both (Sets.programRan 1393) (.both (Sets.programRan 1394) (.both (Sets.programRan 1395) (Sets.programRan 1396)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M254

#print axioms Cert.M254.verified
