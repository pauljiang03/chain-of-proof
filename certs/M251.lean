import ChainOfProof
open ChainOfProof

namespace Cert.M251

def cited : List Fact := [
  ⟨1237, .programRun, 1427034793777763, 1, 790, 0⟩,
  ⟨1238, .programRun, 1427034793777763, 1, 791, 0⟩,
  ⟨1239, .programRun, 1427034793777763, 1, 792, 793⟩,
  ⟨1240, .programRun, 1427034793777763, 1, 794, 795⟩,
  ⟨1241, .programRun, 1427034793777763, 1, 796, 797⟩,
  ⟨1242, .programRun, 1427034793777763, 1, 476, 798⟩,
  ⟨1243, .programRun, 1427034793777763, 1, 799, 800⟩,
  ⟨1244, .programRun, 1427034793777763, 1, 394, 801⟩,
  ⟨1245, .programRun, 1427034793777763, 1, 440, 802⟩,
  ⟨1246, .programRun, 1427034793777763, 1, 447, 803⟩,
  ⟨1247, .programRun, 1427034793777763, 1, 478, 804⟩,
  ⟨1248, .programRun, 1427035866535612, 1, 805, 0⟩,
  ⟨1249, .programRun, 1427036608795117, 1, 806, 807⟩,
  ⟨1250, .programRun, 1427036608795117, 1, 808, 809⟩,
  ⟨1251, .programRun, 1427036608810717, 1, 810, 811⟩,
  ⟨1252, .programRun, 1427036608888718, 1, 812, 813⟩,
  ⟨1253, .programRun, 1427036608888718, 1, 814, 815⟩,
  ⟨1254, .programRun, 1427036608904318, 1, 816, 817⟩,
  ⟨1255, .programRun, 1427036608904318, 1, 818, 819⟩,
  ⟨1256, .programRun, 1427036609060318, 1, 820, 821⟩,
  ⟨1257, .programRun, 1427036609060318, 1, 822, 823⟩,
  ⟨1258, .programRun, 1427036609060318, 1, 824, 825⟩,
  ⟨1259, .programRun, 1427036667435620, 1, 826, 827⟩,
  ⟨1260, .programRun, 1427037064000000, 1, 828, 829⟩,
  ⟨1261, .programRun, 1427037064851735, 1, 830, 831⟩,
  ⟨1262, .programRun, 1427037064851735, 1, 828, 832⟩,
  ⟨1263, .programRun, 1427037064851735, 1, 828, 833⟩,
  ⟨1264, .programRun, 1427037064851735, 1, 828, 834⟩,
  ⟨1265, .programRun, 1427037081456566, 1, 835, 836⟩,
  ⟨1266, .programRun, 1427037081456566, 1, 835, 837⟩,
  ⟨1267, .programRun, 1427037081487766, 1, 838, 839⟩,
  ⟨1268, .programRun, 1427037082751368, 1, 840, 841⟩,
  ⟨1269, .programRun, 1427037086121575, 1, 842, 843⟩,
  ⟨1270, .programRun, 1427037086121575, 1, 840, 844⟩,
  ⟨1271, .programRun, 1427037086121575, 1, 840, 845⟩,
  ⟨1272, .programRun, 1427037086121575, 1, 846, 847⟩,
  ⟨1273, .programRun, 1427037086137175, 1, 848, 849⟩,
  ⟨1274, .programRun, 1427037086137175, 1, 850, 851⟩,
  ⟨1275, .programRun, 1427037103609205, 1, 852, 853⟩,
  ⟨1276, .programRun, 1427037103609205, 1, 854, 855⟩ ]

def claim : Claim := .both (Sets.programRan 1237) (.both (Sets.programRan 1238) (.both (Sets.programRan 1239) (.both (Sets.programRan 1240) (.both (Sets.programRan 1241) (.both (Sets.programRan 1242) (.both (Sets.programRan 1243) (.both (Sets.programRan 1244) (.both (Sets.programRan 1245) (.both (Sets.programRan 1246) (.both (Sets.programRan 1247) (.both (Sets.programRan 1248) (.both (Sets.programRan 1249) (.both (Sets.programRan 1250) (.both (Sets.programRan 1251) (.both (Sets.programRan 1252) (.both (Sets.programRan 1253) (.both (Sets.programRan 1254) (.both (Sets.programRan 1255) (.both (Sets.programRan 1256) (.both (Sets.programRan 1257) (.both (Sets.programRan 1258) (.both (Sets.programRan 1259) (.both (Sets.programRan 1260) (.both (Sets.programRan 1261) (.both (Sets.programRan 1262) (.both (Sets.programRan 1263) (.both (Sets.programRan 1264) (.both (Sets.programRan 1265) (.both (Sets.programRan 1266) (.both (Sets.programRan 1267) (.both (Sets.programRan 1268) (.both (Sets.programRan 1269) (.both (Sets.programRan 1270) (.both (Sets.programRan 1271) (.both (Sets.programRan 1272) (.both (Sets.programRan 1273) (.both (Sets.programRan 1274) (.both (Sets.programRan 1275) (Sets.programRan 1276)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M251

#print axioms Cert.M251.verified
