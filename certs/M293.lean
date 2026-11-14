import ChainOfProof
open ChainOfProof

namespace Cert.M293

def cited : List Fact := [
  ⟨11090, .fileSeen, 1420751302506809, 1, 15481, 15339⟩,
  ⟨11091, .fileSeen, 1422046030000000, 1, 12630, 15339⟩,
  ⟨11092, .fileSeen, 1422636560552011, 1, 15482, 15339⟩,
  ⟨11093, .fileSeen, 1427034865513456, 1, 1456, 15339⟩,
  ⟨11094, .fileSeen, 1427034867409086, 1, 1456, 15339⟩,
  ⟨11095, .fileSeen, 1427034867502686, 1, 15364, 15339⟩,
  ⟨11096, .fileSeen, 1427034867518286, 1, 15404, 15339⟩,
  ⟨11097, .fileSeen, 1427034867689886, 1, 15471, 15339⟩,
  ⟨11098, .fileSeen, 1427034867705486, 1, 15472, 15339⟩,
  ⟨11099, .fileSeen, 1427034867799087, 1, 15402, 15339⟩,
  ⟨11100, .fileSeen, 1427034867814687, 1, 15342, 15339⟩,
  ⟨11101, .fileSeen, 1427034867814687, 1, 15368, 15339⟩,
  ⟨11102, .fileSeen, 1427034867814687, 1, 15406, 15339⟩,
  ⟨11103, .fileSeen, 1427034867830287, 1, 15367, 15339⟩,
  ⟨11104, .fileSeen, 1427034867845887, 1, 15362, 15339⟩,
  ⟨11105, .fileSeen, 1427034867845887, 1, 15347, 15339⟩,
  ⟨11106, .fileSeen, 1427034867845887, 1, 15348, 15339⟩,
  ⟨11107, .fileSeen, 1427034867845887, 1, 15350, 15339⟩,
  ⟨11108, .fileSeen, 1427034867845887, 1, 15349, 15339⟩,
  ⟨11109, .fileSeen, 1427034867939487, 1, 15345, 15339⟩,
  ⟨11110, .fileSeen, 1427034867939487, 1, 15346, 15339⟩,
  ⟨11111, .fileSeen, 1427034867955087, 1, 15343, 15339⟩,
  ⟨11112, .fileSeen, 1427034867955087, 1, 15363, 15339⟩,
  ⟨11113, .fileSeen, 1427034867955087, 1, 15344, 15339⟩,
  ⟨11114, .fileSeen, 1427034868891089, 1, 15447, 15339⟩,
  ⟨11115, .fileSeen, 1427034871433893, 1, 15483, 15339⟩,
  ⟨11116, .fileSeen, 1427034873149896, 1, 15446, 15339⟩,
  ⟨11117, .fileSeen, 1427034873181096, 1, 15483, 15339⟩,
  ⟨11118, .fileSeen, 1427034874288698, 1, 15448, 15339⟩,
  ⟨11119, .fileSeen, 1427034874413498, 1, 15457, 15339⟩,
  ⟨11120, .fileSeen, 1427034874522698, 1, 15452, 15339⟩,
  ⟨11121, .fileSeen, 1427034874538298, 1, 15456, 15339⟩,
  ⟨11122, .fileSeen, 1427034874569498, 1, 15451, 15339⟩,
  ⟨11123, .fileSeen, 1427034875302700, 1, 15455, 15339⟩,
  ⟨11124, .fileSeen, 1427034875333900, 1, 15450, 15339⟩,
  ⟨11125, .fileSeen, 1427034875349500, 1, 15449, 15339⟩,
  ⟨11126, .fileSeen, 1427034875380700, 1, 15454, 15339⟩,
  ⟨11127, .fileSeen, 1427034875427500, 1, 15445, 15339⟩,
  ⟨11128, .fileSeen, 1427034875567900, 1, 15397, 15339⟩,
  ⟨11129, .fileSeen, 1427034876769102, 1, 15466, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11090) (.both (Sets.fileRecorded 11091) (.both (Sets.fileRecorded 11092) (.both (Sets.fileRecorded 11093) (.both (Sets.fileRecorded 11094) (.both (Sets.fileRecorded 11095) (.both (Sets.fileRecorded 11096) (.both (Sets.fileRecorded 11097) (.both (Sets.fileRecorded 11098) (.both (Sets.fileRecorded 11099) (.both (Sets.fileRecorded 11100) (.both (Sets.fileRecorded 11101) (.both (Sets.fileRecorded 11102) (.both (Sets.fileRecorded 11103) (.both (Sets.fileRecorded 11104) (.both (Sets.fileRecorded 11105) (.both (Sets.fileRecorded 11106) (.both (Sets.fileRecorded 11107) (.both (Sets.fileRecorded 11108) (.both (Sets.fileRecorded 11109) (.both (Sets.fileRecorded 11110) (.both (Sets.fileRecorded 11111) (.both (Sets.fileRecorded 11112) (.both (Sets.fileRecorded 11113) (.both (Sets.fileRecorded 11114) (.both (Sets.fileRecorded 11115) (.both (Sets.fileRecorded 11116) (.both (Sets.fileRecorded 11117) (.both (Sets.fileRecorded 11118) (.both (Sets.fileRecorded 11119) (.both (Sets.fileRecorded 11120) (.both (Sets.fileRecorded 11121) (.both (Sets.fileRecorded 11122) (.both (Sets.fileRecorded 11123) (.both (Sets.fileRecorded 11124) (.both (Sets.fileRecorded 11125) (.both (Sets.fileRecorded 11126) (.both (Sets.fileRecorded 11127) (.both (Sets.fileRecorded 11128) (Sets.fileRecorded 11129)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M293

#print axioms Cert.M293.verified
