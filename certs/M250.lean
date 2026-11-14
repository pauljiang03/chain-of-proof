import ChainOfProof
open ChainOfProof

namespace Cert.M250

def cited : List Fact := [
  ⟨1197, .programRun, 1306965436000000, 1, 711, 712⟩,
  ⟨1198, .programRun, 1314759932000000, 1, 713, 714⟩,
  ⟨1199, .programRun, 1349132384000000, 1, 715, 716⟩,
  ⟨1200, .programRun, 1349137532420000, 1, 717, 718⟩,
  ⟨1201, .programRun, 1349138078000000, 1, 719, 720⟩,
  ⟨1202, .programRun, 1349138084000000, 1, 721, 722⟩,
  ⟨1203, .programRun, 1349138142000000, 1, 723, 724⟩,
  ⟨1204, .programRun, 1349138144000000, 1, 725, 726⟩,
  ⟨1205, .programRun, 1349138144000000, 1, 727, 728⟩,
  ⟨1206, .programRun, 1349138162000000, 1, 729, 730⟩,
  ⟨1207, .programRun, 1349138164000000, 1, 731, 732⟩,
  ⟨1208, .programRun, 1349138164000000, 1, 733, 734⟩,
  ⟨1209, .programRun, 1349138196000000, 1, 735, 736⟩,
  ⟨1210, .programRun, 1349138196000000, 1, 737, 738⟩,
  ⟨1211, .programRun, 1349138196000000, 1, 739, 740⟩,
  ⟨1212, .programRun, 1349138196000000, 1, 741, 742⟩,
  ⟨1213, .programRun, 1349138198000000, 1, 743, 744⟩,
  ⟨1214, .programRun, 1349138672187000, 1, 745, 746⟩,
  ⟨1215, .programRun, 1349138672187000, 1, 747, 748⟩,
  ⟨1216, .programRun, 1381790894000000, 1, 749, 750⟩,
  ⟨1217, .programRun, 1381793274000000, 1, 751, 752⟩,
  ⟨1218, .programRun, 1406823354000000, 1, 753, 754⟩,
  ⟨1219, .programRun, 1416590438000000, 1, 755, 756⟩,
  ⟨1220, .programRun, 1416590444000000, 1, 757, 758⟩,
  ⟨1221, .programRun, 1417487170000000, 1, 759, 760⟩,
  ⟨1222, .programRun, 1417487370000000, 1, 761, 762⟩,
  ⟨1223, .programRun, 1421103396000000, 1, 763, 764⟩,
  ⟨1224, .programRun, 1424370264000000, 1, 765, 766⟩,
  ⟨1225, .programRun, 1424370266000000, 1, 767, 768⟩,
  ⟨1226, .programRun, 1424370268000000, 1, 769, 770⟩,
  ⟨1227, .programRun, 1426245026000000, 1, 771, 772⟩,
  ⟨1228, .programRun, 1426245026000000, 1, 773, 774⟩,
  ⟨1229, .programRun, 1426254938000000, 1, 775, 776⟩,
  ⟨1230, .programRun, 1426254938000000, 1, 777, 778⟩,
  ⟨1231, .programRun, 1426327959738399, 1, 779, 780⟩,
  ⟨1232, .programRun, 1426800960000000, 1, 781, 782⟩,
  ⟨1233, .programRun, 1427034793777763, 1, 783, 784⟩,
  ⟨1234, .programRun, 1427034793777763, 1, 785, 786⟩,
  ⟨1235, .programRun, 1427034793777763, 1, 787, 788⟩,
  ⟨1236, .programRun, 1427034793777763, 1, 789, 0⟩ ]

def claim : Claim := .both (Sets.programRan 1197) (.both (Sets.programRan 1198) (.both (Sets.programRan 1199) (.both (Sets.programRan 1200) (.both (Sets.programRan 1201) (.both (Sets.programRan 1202) (.both (Sets.programRan 1203) (.both (Sets.programRan 1204) (.both (Sets.programRan 1205) (.both (Sets.programRan 1206) (.both (Sets.programRan 1207) (.both (Sets.programRan 1208) (.both (Sets.programRan 1209) (.both (Sets.programRan 1210) (.both (Sets.programRan 1211) (.both (Sets.programRan 1212) (.both (Sets.programRan 1213) (.both (Sets.programRan 1214) (.both (Sets.programRan 1215) (.both (Sets.programRan 1216) (.both (Sets.programRan 1217) (.both (Sets.programRan 1218) (.both (Sets.programRan 1219) (.both (Sets.programRan 1220) (.both (Sets.programRan 1221) (.both (Sets.programRan 1222) (.both (Sets.programRan 1223) (.both (Sets.programRan 1224) (.both (Sets.programRan 1225) (.both (Sets.programRan 1226) (.both (Sets.programRan 1227) (.both (Sets.programRan 1228) (.both (Sets.programRan 1229) (.both (Sets.programRan 1230) (.both (Sets.programRan 1231) (.both (Sets.programRan 1232) (.both (Sets.programRan 1233) (.both (Sets.programRan 1234) (.both (Sets.programRan 1235) (Sets.programRan 1236)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M250

#print axioms Cert.M250.verified
