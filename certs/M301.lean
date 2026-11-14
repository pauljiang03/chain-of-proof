import ChainOfProof
open ChainOfProof

namespace Cert.M301

def cited : List Fact := [
  ⟨11410, .fileSeen, 1427034902867949, 1, 15651, 15545⟩,
  ⟨11411, .fileSeen, 1427034902867949, 1, 15652, 15545⟩,
  ⟨11412, .fileSeen, 1427034902867949, 1, 15653, 15545⟩,
  ⟨11413, .fileSeen, 1427034902867949, 1, 15654, 15545⟩,
  ⟨11414, .fileSeen, 1427034902867949, 1, 15655, 15545⟩,
  ⟨11415, .fileSeen, 1427034902867949, 1, 15656, 15545⟩,
  ⟨11416, .fileSeen, 1427034902867949, 1, 15657, 15545⟩,
  ⟨11417, .fileSeen, 1427034902867949, 1, 15658, 15545⟩,
  ⟨11418, .fileSeen, 1427034902867949, 1, 15659, 15545⟩,
  ⟨11419, .fileSeen, 1427034902867949, 1, 15660, 15545⟩,
  ⟨11420, .fileSeen, 1427034902867949, 1, 15661, 15545⟩,
  ⟨11421, .fileSeen, 1427034902867949, 1, 15662, 15545⟩,
  ⟨11422, .fileSeen, 1427034902867949, 1, 15663, 15545⟩,
  ⟨11423, .fileSeen, 1427034902867949, 1, 15664, 15545⟩,
  ⟨11424, .fileSeen, 1427034902867949, 1, 15665, 15545⟩,
  ⟨11425, .fileSeen, 1427034902867949, 1, 15666, 15545⟩,
  ⟨11426, .fileSeen, 1427034902867949, 1, 15667, 15545⟩,
  ⟨11427, .fileSeen, 1427034902867949, 1, 15668, 15545⟩,
  ⟨11428, .fileSeen, 1427034902867949, 1, 15669, 15545⟩,
  ⟨11429, .fileSeen, 1427034902867949, 1, 15670, 15545⟩,
  ⟨11430, .fileSeen, 1427034902867949, 1, 15671, 15545⟩,
  ⟨11431, .fileSeen, 1427034902867949, 1, 15672, 15545⟩,
  ⟨11432, .fileSeen, 1427034902867949, 1, 15673, 15545⟩,
  ⟨11433, .fileSeen, 1427034902867949, 1, 15674, 15545⟩,
  ⟨11434, .fileSeen, 1427034902867949, 1, 15675, 15545⟩,
  ⟨11435, .fileSeen, 1427034902867949, 1, 15676, 15545⟩,
  ⟨11436, .fileSeen, 1427034902867949, 1, 15677, 15545⟩,
  ⟨11437, .fileSeen, 1427034902867949, 1, 15678, 15545⟩,
  ⟨11438, .fileSeen, 1427034902867949, 1, 15679, 15545⟩,
  ⟨11439, .fileSeen, 1427034902867949, 1, 15680, 15545⟩,
  ⟨11440, .fileSeen, 1427034902867949, 1, 15681, 15545⟩,
  ⟨11441, .fileSeen, 1427034902867949, 1, 15682, 15545⟩,
  ⟨11442, .fileSeen, 1427034902867949, 1, 15683, 15545⟩,
  ⟨11443, .fileSeen, 1427034902867949, 1, 15684, 15545⟩,
  ⟨11444, .fileSeen, 1427034902867949, 1, 15685, 15545⟩,
  ⟨11445, .fileSeen, 1427034902867949, 1, 15686, 15545⟩,
  ⟨11446, .fileSeen, 1427034902867949, 1, 15687, 15545⟩,
  ⟨11447, .fileSeen, 1427034902867949, 1, 15688, 15545⟩,
  ⟨11448, .fileSeen, 1427034902867949, 1, 15689, 15545⟩,
  ⟨11449, .fileSeen, 1427034902867949, 1, 15690, 15545⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11410) (.both (Sets.fileRecorded 11411) (.both (Sets.fileRecorded 11412) (.both (Sets.fileRecorded 11413) (.both (Sets.fileRecorded 11414) (.both (Sets.fileRecorded 11415) (.both (Sets.fileRecorded 11416) (.both (Sets.fileRecorded 11417) (.both (Sets.fileRecorded 11418) (.both (Sets.fileRecorded 11419) (.both (Sets.fileRecorded 11420) (.both (Sets.fileRecorded 11421) (.both (Sets.fileRecorded 11422) (.both (Sets.fileRecorded 11423) (.both (Sets.fileRecorded 11424) (.both (Sets.fileRecorded 11425) (.both (Sets.fileRecorded 11426) (.both (Sets.fileRecorded 11427) (.both (Sets.fileRecorded 11428) (.both (Sets.fileRecorded 11429) (.both (Sets.fileRecorded 11430) (.both (Sets.fileRecorded 11431) (.both (Sets.fileRecorded 11432) (.both (Sets.fileRecorded 11433) (.both (Sets.fileRecorded 11434) (.both (Sets.fileRecorded 11435) (.both (Sets.fileRecorded 11436) (.both (Sets.fileRecorded 11437) (.both (Sets.fileRecorded 11438) (.both (Sets.fileRecorded 11439) (.both (Sets.fileRecorded 11440) (.both (Sets.fileRecorded 11441) (.both (Sets.fileRecorded 11442) (.both (Sets.fileRecorded 11443) (.both (Sets.fileRecorded 11444) (.both (Sets.fileRecorded 11445) (.both (Sets.fileRecorded 11446) (.both (Sets.fileRecorded 11447) (.both (Sets.fileRecorded 11448) (Sets.fileRecorded 11449)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M301

#print axioms Cert.M301.verified
