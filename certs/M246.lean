import ChainOfProof
open ChainOfProof

namespace Cert.M246

def cited : List Fact := [
  ⟨1037, .programRun, 1247535548502000, 1, 425, 426⟩,
  ⟨1038, .programRun, 1247535548549000, 1, 427, 428⟩,
  ⟨1039, .programRun, 1247535549173000, 1, 429, 430⟩,
  ⟨1040, .programRun, 1247535552464000, 1, 431, 432⟩,
  ⟨1041, .programRun, 1247535553540000, 1, 433, 434⟩,
  ⟨1042, .programRun, 1247535555849000, 1, 371, 435⟩,
  ⟨1043, .programRun, 1247535556114000, 1, 436, 437⟩,
  ⟨1044, .programRun, 1247535556114000, 1, 438, 439⟩,
  ⟨1045, .programRun, 1247535556660000, 1, 440, 441⟩,
  ⟨1046, .programRun, 1247535557378000, 1, 442, 443⟩,
  ⟨1047, .programRun, 1247535560030000, 1, 373, 444⟩,
  ⟨1048, .programRun, 1247535560342000, 1, 445, 446⟩,
  ⟨1049, .programRun, 1247535564211000, 1, 447, 448⟩,
  ⟨1050, .programRun, 1247535564367000, 1, 449, 450⟩,
  ⟨1051, .programRun, 1247535565209000, 1, 451, 452⟩,
  ⟨1052, .programRun, 1247535565490000, 1, 453, 454⟩,
  ⟨1053, .programRun, 1247535566317000, 1, 455, 456⟩,
  ⟨1054, .programRun, 1247535566816000, 1, 457, 458⟩,
  ⟨1055, .programRun, 1247535567081000, 1, 459, 460⟩,
  ⟨1056, .programRun, 1247535569733000, 1, 461, 462⟩,
  ⟨1057, .programRun, 1247535571433000, 1, 379, 463⟩,
  ⟨1058, .programRun, 1247535575942000, 1, 464, 465⟩,
  ⟨1059, .programRun, 1247535577002000, 1, 466, 467⟩,
  ⟨1060, .programRun, 1247535577049000, 1, 468, 469⟩,
  ⟨1061, .programRun, 1247535577283000, 1, 470, 471⟩,
  ⟨1062, .programRun, 1247535577408000, 1, 472, 473⟩,
  ⟨1063, .programRun, 1247535577595000, 1, 474, 475⟩,
  ⟨1064, .programRun, 1247535581745000, 1, 476, 477⟩,
  ⟨1065, .programRun, 1247535582072000, 1, 478, 479⟩,
  ⟨1066, .programRun, 1247535586409000, 1, 480, 481⟩,
  ⟨1067, .programRun, 1247535586503000, 1, 482, 483⟩,
  ⟨1068, .programRun, 1247535588671000, 1, 484, 485⟩,
  ⟨1069, .programRun, 1247535588811000, 1, 486, 487⟩,
  ⟨1070, .programRun, 1247535589810000, 1, 488, 489⟩,
  ⟨1071, .programRun, 1247535591775000, 1, 490, 491⟩,
  ⟨1072, .programRun, 1247535591853000, 1, 383, 492⟩,
  ⟨1073, .programRun, 1247535593023000, 1, 386, 493⟩,
  ⟨1074, .programRun, 1247535595082000, 1, 494, 495⟩,
  ⟨1075, .programRun, 1247535596611000, 1, 496, 497⟩,
  ⟨1076, .programRun, 1247535597719000, 1, 498, 499⟩ ]

def claim : Claim := .both (Sets.programRan 1037) (.both (Sets.programRan 1038) (.both (Sets.programRan 1039) (.both (Sets.programRan 1040) (.both (Sets.programRan 1041) (.both (Sets.programRan 1042) (.both (Sets.programRan 1043) (.both (Sets.programRan 1044) (.both (Sets.programRan 1045) (.both (Sets.programRan 1046) (.both (Sets.programRan 1047) (.both (Sets.programRan 1048) (.both (Sets.programRan 1049) (.both (Sets.programRan 1050) (.both (Sets.programRan 1051) (.both (Sets.programRan 1052) (.both (Sets.programRan 1053) (.both (Sets.programRan 1054) (.both (Sets.programRan 1055) (.both (Sets.programRan 1056) (.both (Sets.programRan 1057) (.both (Sets.programRan 1058) (.both (Sets.programRan 1059) (.both (Sets.programRan 1060) (.both (Sets.programRan 1061) (.both (Sets.programRan 1062) (.both (Sets.programRan 1063) (.both (Sets.programRan 1064) (.both (Sets.programRan 1065) (.both (Sets.programRan 1066) (.both (Sets.programRan 1067) (.both (Sets.programRan 1068) (.both (Sets.programRan 1069) (.both (Sets.programRan 1070) (.both (Sets.programRan 1071) (.both (Sets.programRan 1072) (.both (Sets.programRan 1073) (.both (Sets.programRan 1074) (.both (Sets.programRan 1075) (Sets.programRan 1076)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M246

#print axioms Cert.M246.verified
