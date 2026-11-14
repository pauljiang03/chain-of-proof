import ChainOfProof
open ChainOfProof

namespace Cert.M307

def cited : List Fact := [
  ⟨11650, .fileSeen, 1427036609419118, 1, 15856, 15339⟩,
  ⟨11651, .fileSeen, 1427036609419118, 1, 15857, 15339⟩,
  ⟨11652, .fileSeen, 1427036609434719, 1, 15847, 15339⟩,
  ⟨11653, .fileSeen, 1427036609434719, 1, 15858, 15339⟩,
  ⟨11654, .fileSeen, 1427036903167634, 1, 15546, 15339⟩,
  ⟨11655, .fileSeen, 1427036915867858, 1, 15546, 15339⟩,
  ⟨11656, .fileSeen, 1427036940952702, 1, 15489, 15339⟩,
  ⟨11657, .fileSeen, 1427036941904304, 1, 15525, 15339⟩,
  ⟨11658, .fileSeen, 1427036941904304, 1, 15841, 15339⟩,
  ⟨11659, .fileSeen, 1427036941904304, 1, 15534, 15339⟩,
  ⟨11660, .fileSeen, 1427036941919904, 1, 15522, 15339⟩,
  ⟨11661, .fileSeen, 1427036957878732, 1, 15539, 15339⟩,
  ⟨11662, .fileSeen, 1427036957878732, 1, 15859, 15339⟩,
  ⟨11663, .fileSeen, 1427036962000000, 1, 1099, 15339⟩,
  ⟨11664, .fileSeen, 1427036963494000, 1, 1096, 15339⟩,
  ⟨11665, .fileSeen, 1427036979010971, 1, 1099, 15339⟩,
  ⟨11666, .fileSeen, 1427036979010971, 1, 1100, 15339⟩,
  ⟨11667, .fileSeen, 1427036980000000, 1, 1100, 15339⟩,
  ⟨11668, .fileSeen, 1427036988560389, 1, 1102, 15339⟩,
  ⟨11669, .fileSeen, 1427036990000000, 1, 1102, 15339⟩,
  ⟨11670, .fileSeen, 1427036992000000, 1, 1103, 15339⟩,
  ⟨11671, .fileSeen, 1427036992421397, 1, 1103, 15339⟩,
  ⟨11672, .fileSeen, 1427036994000000, 1, 1104, 15339⟩,
  ⟨11673, .fileSeen, 1427036994262200, 1, 1104, 15339⟩,
  ⟨11674, .fileSeen, 1427036994371401, 1, 1105, 15339⟩,
  ⟨11675, .fileSeen, 1427036996000000, 1, 1105, 15339⟩,
  ⟨11676, .fileSeen, 1427037024000000, 1, 1106, 15339⟩,
  ⟨11677, .fileSeen, 1427037031472071, 1, 1106, 15339⟩,
  ⟨11678, .fileSeen, 1427037052056510, 1, 1107, 15339⟩,
  ⟨11679, .fileSeen, 1427037054000000, 1, 1107, 15339⟩,
  ⟨11680, .fileSeen, 1427037058000000, 1, 1108, 15339⟩,
  ⟨11681, .fileSeen, 1427037064087333, 1, 833, 15339⟩,
  ⟨11682, .fileSeen, 1427037064851735, 1, 833, 15339⟩,
  ⟨11683, .fileSeen, 1427037064851735, 1, 834, 15453⟩,
  ⟨11684, .fileSeen, 1427037064851735, 1, 834, 15339⟩,
  ⟨11685, .fileSeen, 1427037066000000, 1, 1109, 15339⟩,
  ⟨11686, .fileSeen, 1427037066396139, 1, 1109, 15339⟩,
  ⟨11687, .fileSeen, 1427037066411739, 1, 833, 15339⟩,
  ⟨11688, .fileSeen, 1427037066411739, 1, 1108, 15339⟩,
  ⟨11689, .fileSeen, 1427037074732954, 1, 1111, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11650) (.both (Sets.fileRecorded 11651) (.both (Sets.fileRecorded 11652) (.both (Sets.fileRecorded 11653) (.both (Sets.fileRecorded 11654) (.both (Sets.fileRecorded 11655) (.both (Sets.fileRecorded 11656) (.both (Sets.fileRecorded 11657) (.both (Sets.fileRecorded 11658) (.both (Sets.fileRecorded 11659) (.both (Sets.fileRecorded 11660) (.both (Sets.fileRecorded 11661) (.both (Sets.fileRecorded 11662) (.both (Sets.fileRecorded 11663) (.both (Sets.fileRecorded 11664) (.both (Sets.fileRecorded 11665) (.both (Sets.fileRecorded 11666) (.both (Sets.fileRecorded 11667) (.both (Sets.fileRecorded 11668) (.both (Sets.fileRecorded 11669) (.both (Sets.fileRecorded 11670) (.both (Sets.fileRecorded 11671) (.both (Sets.fileRecorded 11672) (.both (Sets.fileRecorded 11673) (.both (Sets.fileRecorded 11674) (.both (Sets.fileRecorded 11675) (.both (Sets.fileRecorded 11676) (.both (Sets.fileRecorded 11677) (.both (Sets.fileRecorded 11678) (.both (Sets.fileRecorded 11679) (.both (Sets.fileRecorded 11680) (.both (Sets.fileRecorded 11681) (.both (Sets.fileRecorded 11682) (.both (Sets.fileRecorded 11683) (.both (Sets.fileRecorded 11684) (.both (Sets.fileRecorded 11685) (.both (Sets.fileRecorded 11686) (.both (Sets.fileRecorded 11687) (.both (Sets.fileRecorded 11688) (Sets.fileRecorded 11689)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M307

#print axioms Cert.M307.verified
