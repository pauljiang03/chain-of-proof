import ChainOfProof
open ChainOfProof

namespace Cert.M248

def cited : List Fact := [
  ⟨1117, .programRun, 1290309836530903, 1, 571, 572⟩,
  ⟨1118, .programRun, 1290309840415310, 1, 573, 574⟩,
  ⟨1119, .programRun, 1290309841023711, 1, 552, 575⟩,
  ⟨1120, .programRun, 1290309841148511, 1, 484, 576⟩,
  ⟨1121, .programRun, 1290309841195311, 1, 577, 578⟩,
  ⟨1122, .programRun, 1290309841632112, 1, 579, 580⟩,
  ⟨1123, .programRun, 1290309842724114, 1, 581, 582⟩,
  ⟨1124, .programRun, 1290309843238915, 1, 583, 584⟩,
  ⟨1125, .programRun, 1290309843332515, 1, 567, 568⟩,
  ⟨1126, .programRun, 1290309843332515, 1, 567, 585⟩,
  ⟨1127, .programRun, 1290309843332515, 1, 586, 587⟩,
  ⟨1128, .programRun, 1290309847482122, 1, 563, 588⟩,
  ⟨1129, .programRun, 1290309847638122, 1, 589, 590⟩,
  ⟨1130, .programRun, 1290309848246523, 1, 591, 592⟩,
  ⟨1131, .programRun, 1290309848418124, 1, 593, 594⟩,
  ⟨1132, .programRun, 1290309848527324, 1, 595, 596⟩,
  ⟨1133, .programRun, 1290309848527324, 1, 595, 597⟩,
  ⟨1134, .programRun, 1290309848964125, 1, 598, 599⟩,
  ⟨1135, .programRun, 1290309849151325, 1, 600, 601⟩,
  ⟨1136, .programRun, 1290309849572526, 1, 602, 603⟩,
  ⟨1137, .programRun, 1290309849619326, 1, 604, 605⟩,
  ⟨1138, .programRun, 1290309849650526, 1, 606, 607⟩,
  ⟨1139, .programRun, 1290309850134127, 1, 608, 609⟩,
  ⟨1140, .programRun, 1290309851678529, 1, 610, 611⟩,
  ⟨1141, .programRun, 1290309855235336, 1, 612, 613⟩,
  ⟨1142, .programRun, 1290309855469336, 1, 614, 615⟩,
  ⟨1143, .programRun, 1290309855500536, 1, 616, 617⟩,
  ⟨1144, .programRun, 1290309855656536, 1, 581, 618⟩,
  ⟨1145, .programRun, 1290309856077737, 1, 619, 620⟩,
  ⟨1146, .programRun, 1290309856935739, 1, 621, 622⟩,
  ⟨1147, .programRun, 1290309862848149, 1, 623, 624⟩,
  ⟨1148, .programRun, 1290309863503350, 1, 604, 625⟩,
  ⟨1149, .programRun, 1290309863612550, 1, 626, 627⟩,
  ⟨1150, .programRun, 1290309864064951, 1, 628, 629⟩,
  ⟨1151, .programRun, 1290309864626552, 1, 630, 631⟩,
  ⟨1152, .programRun, 1290309865078953, 1, 632, 633⟩,
  ⟨1153, .programRun, 1290309865078953, 1, 632, 634⟩,
  ⟨1154, .programRun, 1290309865234953, 1, 635, 636⟩,
  ⟨1155, .programRun, 1290309866170955, 1, 637, 638⟩,
  ⟨1156, .programRun, 1290309866280155, 1, 639, 640⟩ ]

def claim : Claim := .both (Sets.programRan 1117) (.both (Sets.programRan 1118) (.both (Sets.programRan 1119) (.both (Sets.programRan 1120) (.both (Sets.programRan 1121) (.both (Sets.programRan 1122) (.both (Sets.programRan 1123) (.both (Sets.programRan 1124) (.both (Sets.programRan 1125) (.both (Sets.programRan 1126) (.both (Sets.programRan 1127) (.both (Sets.programRan 1128) (.both (Sets.programRan 1129) (.both (Sets.programRan 1130) (.both (Sets.programRan 1131) (.both (Sets.programRan 1132) (.both (Sets.programRan 1133) (.both (Sets.programRan 1134) (.both (Sets.programRan 1135) (.both (Sets.programRan 1136) (.both (Sets.programRan 1137) (.both (Sets.programRan 1138) (.both (Sets.programRan 1139) (.both (Sets.programRan 1140) (.both (Sets.programRan 1141) (.both (Sets.programRan 1142) (.both (Sets.programRan 1143) (.both (Sets.programRan 1144) (.both (Sets.programRan 1145) (.both (Sets.programRan 1146) (.both (Sets.programRan 1147) (.both (Sets.programRan 1148) (.both (Sets.programRan 1149) (.both (Sets.programRan 1150) (.both (Sets.programRan 1151) (.both (Sets.programRan 1152) (.both (Sets.programRan 1153) (.both (Sets.programRan 1154) (.both (Sets.programRan 1155) (Sets.programRan 1156)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M248

#print axioms Cert.M248.verified
