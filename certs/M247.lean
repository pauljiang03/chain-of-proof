import ChainOfProof
open ChainOfProof

namespace Cert.M247

def cited : List Fact := [
  ⟨1077, .programRun, 1247535599638000, 1, 500, 501⟩,
  ⟨1078, .programRun, 1247535624145000, 1, 502, 503⟩,
  ⟨1079, .programRun, 1247535628606000, 1, 504, 505⟩,
  ⟨1080, .programRun, 1247535631133000, 1, 506, 507⟩,
  ⟨1081, .programRun, 1247535632413000, 1, 508, 509⟩,
  ⟨1082, .programRun, 1247535636843000, 1, 388, 510⟩,
  ⟨1083, .programRun, 1247535713391000, 1, 511, 512⟩,
  ⟨1084, .programRun, 1247535713859000, 1, 513, 514⟩,
  ⟨1085, .programRun, 1247535713890000, 1, 515, 516⟩,
  ⟨1086, .programRun, 1247535713983000, 1, 517, 518⟩,
  ⟨1087, .programRun, 1247535714654000, 1, 519, 520⟩,
  ⟨1088, .programRun, 1247535716214000, 1, 521, 522⟩,
  ⟨1089, .programRun, 1247535717618000, 1, 523, 524⟩,
  ⟨1090, .programRun, 1247535719147000, 1, 525, 526⟩,
  ⟨1091, .programRun, 1268932588000000, 1, 527, 528⟩,
  ⟨1092, .programRun, 1268932588000000, 1, 366, 529⟩,
  ⟨1093, .programRun, 1268932588000000, 1, 530, 531⟩,
  ⟨1094, .programRun, 1268932588000000, 1, 532, 533⟩,
  ⟨1095, .programRun, 1268936834000000, 1, 527, 534⟩,
  ⟨1096, .programRun, 1268936834000000, 1, 366, 535⟩,
  ⟨1097, .programRun, 1268936834000000, 1, 530, 536⟩,
  ⟨1098, .programRun, 1268936834000000, 1, 532, 537⟩,
  ⟨1099, .programRun, 1268942316000000, 1, 538, 539⟩,
  ⟨1100, .programRun, 1268943388000000, 1, 540, 541⟩,
  ⟨1101, .programRun, 1268945242000000, 1, 542, 543⟩,
  ⟨1102, .programRun, 1268947384000000, 1, 542, 544⟩,
  ⟨1103, .programRun, 1268955157000000, 1, 545, 546⟩,
  ⟨1104, .programRun, 1268959868000000, 1, 547, 548⟩,
  ⟨1105, .programRun, 1290309828824489, 1, 530, 549⟩,
  ⟨1106, .programRun, 1290309828964890, 1, 550, 551⟩,
  ⟨1107, .programRun, 1290309831367294, 1, 552, 553⟩,
  ⟨1108, .programRun, 1290309831414094, 1, 554, 555⟩,
  ⟨1109, .programRun, 1290309831414094, 1, 554, 556⟩,
  ⟨1110, .programRun, 1290309831554494, 1, 557, 558⟩,
  ⟨1111, .programRun, 1290309832396896, 1, 559, 560⟩,
  ⟨1112, .programRun, 1290309833972498, 1, 561, 562⟩,
  ⟨1113, .programRun, 1290309834393699, 1, 563, 564⟩,
  ⟨1114, .programRun, 1290309835360901, 1, 565, 566⟩,
  ⟨1115, .programRun, 1290309835532501, 1, 567, 568⟩,
  ⟨1116, .programRun, 1290309836484103, 1, 569, 570⟩ ]

def claim : Claim := .both (Sets.programRan 1077) (.both (Sets.programRan 1078) (.both (Sets.programRan 1079) (.both (Sets.programRan 1080) (.both (Sets.programRan 1081) (.both (Sets.programRan 1082) (.both (Sets.programRan 1083) (.both (Sets.programRan 1084) (.both (Sets.programRan 1085) (.both (Sets.programRan 1086) (.both (Sets.programRan 1087) (.both (Sets.programRan 1088) (.both (Sets.programRan 1089) (.both (Sets.programRan 1090) (.both (Sets.programRan 1091) (.both (Sets.programRan 1092) (.both (Sets.programRan 1093) (.both (Sets.programRan 1094) (.both (Sets.programRan 1095) (.both (Sets.programRan 1096) (.both (Sets.programRan 1097) (.both (Sets.programRan 1098) (.both (Sets.programRan 1099) (.both (Sets.programRan 1100) (.both (Sets.programRan 1101) (.both (Sets.programRan 1102) (.both (Sets.programRan 1103) (.both (Sets.programRan 1104) (.both (Sets.programRan 1105) (.both (Sets.programRan 1106) (.both (Sets.programRan 1107) (.both (Sets.programRan 1108) (.both (Sets.programRan 1109) (.both (Sets.programRan 1110) (.both (Sets.programRan 1111) (.both (Sets.programRan 1112) (.both (Sets.programRan 1113) (.both (Sets.programRan 1114) (.both (Sets.programRan 1115) (Sets.programRan 1116)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M247

#print axioms Cert.M247.verified
