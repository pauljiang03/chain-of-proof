import ChainOfProof
open ChainOfProof

namespace Cert.M249

def cited : List Fact := [
  ⟨1157, .programRun, 1290309866326955, 1, 554, 555⟩,
  ⟨1158, .programRun, 1290309867122557, 1, 641, 642⟩,
  ⟨1159, .programRun, 1290309867184957, 1, 643, 644⟩,
  ⟨1160, .programRun, 1290309867637357, 1, 645, 646⟩,
  ⟨1161, .programRun, 1290309868386159, 1, 647, 648⟩,
  ⟨1162, .programRun, 1290309868464159, 1, 649, 650⟩,
  ⟨1163, .programRun, 1290309868604559, 1, 651, 652⟩,
  ⟨1164, .programRun, 1290309868807360, 1, 653, 654⟩,
  ⟨1165, .programRun, 1290309868807360, 1, 612, 613⟩,
  ⟨1166, .programRun, 1290309868932160, 1, 655, 656⟩,
  ⟨1167, .programRun, 1290309872410966, 1, 619, 657⟩,
  ⟨1168, .programRun, 1290309872457766, 1, 530, 658⟩,
  ⟨1169, .programRun, 1290309872473366, 1, 626, 659⟩,
  ⟨1170, .programRun, 1290309872769767, 1, 660, 661⟩,
  ⟨1171, .programRun, 1290309875733772, 1, 662, 663⟩,
  ⟨1172, .programRun, 1290309881427782, 1, 664, 665⟩,
  ⟨1173, .programRun, 1290309882831784, 1, 666, 667⟩,
  ⟨1174, .programRun, 1290309883034585, 1, 668, 669⟩,
  ⟨1175, .programRun, 1290309889087395, 1, 670, 671⟩,
  ⟨1176, .programRun, 1290309889134195, 1, 672, 673⟩,
  ⟨1177, .programRun, 1290309891364999, 1, 674, 675⟩,
  ⟨1178, .programRun, 1290309891458599, 1, 676, 677⟩,
  ⟨1179, .programRun, 1290309891474199, 1, 678, 679⟩,
  ⟨1180, .programRun, 1290309891536599, 1, 680, 681⟩,
  ⟨1181, .programRun, 1290309892113800, 1, 682, 683⟩,
  ⟨1182, .programRun, 1290309892581801, 1, 684, 685⟩,
  ⟨1183, .programRun, 1290309892800202, 1, 686, 687⟩,
  ⟨1184, .programRun, 1290309905061823, 1, 688, 689⟩,
  ⟨1185, .programRun, 1290309905155423, 1, 690, 691⟩,
  ⟨1186, .programRun, 1290309906029025, 1, 692, 693⟩,
  ⟨1187, .programRun, 1290309906325425, 1, 694, 695⟩,
  ⟨1188, .programRun, 1290309906419026, 1, 696, 697⟩,
  ⟨1189, .programRun, 1290309907199027, 1, 698, 699⟩,
  ⟨1190, .programRun, 1290309908010228, 1, 431, 700⟩,
  ⟨1191, .programRun, 1290309908603029, 1, 457, 701⟩,
  ⟨1192, .programRun, 1290309908852630, 1, 668, 702⟩,
  ⟨1193, .programRun, 1290309908977430, 1, 703, 704⟩,
  ⟨1194, .programRun, 1290309909102230, 1, 705, 706⟩,
  ⟨1195, .programRun, 1290309910521833, 1, 707, 708⟩,
  ⟨1196, .programRun, 1290309910584233, 1, 709, 710⟩ ]

def claim : Claim := .both (Sets.programRan 1157) (.both (Sets.programRan 1158) (.both (Sets.programRan 1159) (.both (Sets.programRan 1160) (.both (Sets.programRan 1161) (.both (Sets.programRan 1162) (.both (Sets.programRan 1163) (.both (Sets.programRan 1164) (.both (Sets.programRan 1165) (.both (Sets.programRan 1166) (.both (Sets.programRan 1167) (.both (Sets.programRan 1168) (.both (Sets.programRan 1169) (.both (Sets.programRan 1170) (.both (Sets.programRan 1171) (.both (Sets.programRan 1172) (.both (Sets.programRan 1173) (.both (Sets.programRan 1174) (.both (Sets.programRan 1175) (.both (Sets.programRan 1176) (.both (Sets.programRan 1177) (.both (Sets.programRan 1178) (.both (Sets.programRan 1179) (.both (Sets.programRan 1180) (.both (Sets.programRan 1181) (.both (Sets.programRan 1182) (.both (Sets.programRan 1183) (.both (Sets.programRan 1184) (.both (Sets.programRan 1185) (.both (Sets.programRan 1186) (.both (Sets.programRan 1187) (.both (Sets.programRan 1188) (.both (Sets.programRan 1189) (.both (Sets.programRan 1190) (.both (Sets.programRan 1191) (.both (Sets.programRan 1192) (.both (Sets.programRan 1193) (.both (Sets.programRan 1194) (.both (Sets.programRan 1195) (Sets.programRan 1196)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M249

#print axioms Cert.M249.verified
