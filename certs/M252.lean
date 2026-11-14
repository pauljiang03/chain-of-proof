import ChainOfProof
open ChainOfProof

namespace Cert.M252

def cited : List Fact := [
  ⟨1277, .programRun, 1427037152562000, 1, 828, 833⟩,
  ⟨1278, .programRun, 1427037347515714, 1, 591, 592⟩,
  ⟨1279, .programRun, 1427037412895429, 1, 457, 856⟩,
  ⟨1280, .programRun, 1427037414346232, 1, 431, 432⟩,
  ⟨1281, .programRun, 1427037414954633, 1, 666, 667⟩,
  ⟨1282, .programRun, 1427037415063833, 1, 857, 858⟩,
  ⟨1283, .programRun, 1427037415063833, 1, 857, 859⟩,
  ⟨1284, .programRun, 1427037416499035, 1, 860, 861⟩,
  ⟨1285, .programRun, 1427037416499035, 1, 860, 862⟩,
  ⟨1286, .programRun, 1427037416545835, 1, 863, 864⟩,
  ⟨1287, .programRun, 1427037416545835, 1, 668, 669⟩,
  ⟨1288, .programRun, 1427037418417839, 1, 857, 865⟩,
  ⟨1289, .programRun, 1427037418417839, 1, 857, 866⟩,
  ⟨1290, .programRun, 1427037419307040, 1, 457, 867⟩,
  ⟨1291, .programRun, 1427037419790641, 1, 868, 869⟩,
  ⟨1292, .programRun, 1427037420492642, 1, 666, 870⟩,
  ⟨1293, .programRun, 1427037421116643, 1, 860, 871⟩,
  ⟨1294, .programRun, 1427037421116643, 1, 860, 872⟩,
  ⟨1295, .programRun, 1427037421163443, 1, 863, 873⟩,
  ⟨1296, .programRun, 1427037421225844, 1, 749, 874⟩,
  ⟨1297, .programRun, 1427037887969000, 1, 621, 875⟩,
  ⟨1298, .programRun, 1427039535999162, 1, 783, 784⟩,
  ⟨1299, .programRun, 1427039535999162, 1, 785, 786⟩,
  ⟨1300, .programRun, 1427039535999162, 1, 787, 788⟩,
  ⟨1301, .programRun, 1427039535999162, 1, 789, 0⟩,
  ⟨1302, .programRun, 1427039535999162, 1, 790, 0⟩,
  ⟨1303, .programRun, 1427039535999162, 1, 791, 0⟩,
  ⟨1304, .programRun, 1427039535999162, 1, 876, 0⟩,
  ⟨1305, .programRun, 1427039535999162, 1, 792, 793⟩,
  ⟨1306, .programRun, 1427039535999162, 1, 794, 795⟩,
  ⟨1307, .programRun, 1427039535999162, 1, 796, 797⟩,
  ⟨1308, .programRun, 1427039535999162, 1, 476, 798⟩,
  ⟨1309, .programRun, 1427039535999162, 1, 877, 878⟩,
  ⟨1310, .programRun, 1427039535999162, 1, 799, 800⟩,
  ⟨1311, .programRun, 1427039535999162, 1, 394, 801⟩,
  ⟨1312, .programRun, 1427039535999162, 1, 440, 802⟩,
  ⟨1313, .programRun, 1427039535999162, 1, 447, 803⟩,
  ⟨1314, .programRun, 1427039535999162, 1, 478, 804⟩,
  ⟨1315, .programRun, 1427039535999162, 1, 879, 880⟩,
  ⟨1316, .programRun, 1427039660274498, 1, 783, 784⟩ ]

def claim : Claim := .both (Sets.programRan 1277) (.both (Sets.programRan 1278) (.both (Sets.programRan 1279) (.both (Sets.programRan 1280) (.both (Sets.programRan 1281) (.both (Sets.programRan 1282) (.both (Sets.programRan 1283) (.both (Sets.programRan 1284) (.both (Sets.programRan 1285) (.both (Sets.programRan 1286) (.both (Sets.programRan 1287) (.both (Sets.programRan 1288) (.both (Sets.programRan 1289) (.both (Sets.programRan 1290) (.both (Sets.programRan 1291) (.both (Sets.programRan 1292) (.both (Sets.programRan 1293) (.both (Sets.programRan 1294) (.both (Sets.programRan 1295) (.both (Sets.programRan 1296) (.both (Sets.programRan 1297) (.both (Sets.programRan 1298) (.both (Sets.programRan 1299) (.both (Sets.programRan 1300) (.both (Sets.programRan 1301) (.both (Sets.programRan 1302) (.both (Sets.programRan 1303) (.both (Sets.programRan 1304) (.both (Sets.programRan 1305) (.both (Sets.programRan 1306) (.both (Sets.programRan 1307) (.both (Sets.programRan 1308) (.both (Sets.programRan 1309) (.both (Sets.programRan 1310) (.both (Sets.programRan 1311) (.both (Sets.programRan 1312) (.both (Sets.programRan 1313) (.both (Sets.programRan 1314) (.both (Sets.programRan 1315) (Sets.programRan 1316)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M252

#print axioms Cert.M252.verified
