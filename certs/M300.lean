import ChainOfProof
open ChainOfProof

namespace Cert.M300

def cited : List Fact := [
  ⟨11370, .fileSeen, 1427034902867949, 1, 15611, 15545⟩,
  ⟨11371, .fileSeen, 1427034902867949, 1, 15612, 15545⟩,
  ⟨11372, .fileSeen, 1427034902867949, 1, 15613, 15545⟩,
  ⟨11373, .fileSeen, 1427034902867949, 1, 15614, 15545⟩,
  ⟨11374, .fileSeen, 1427034902867949, 1, 15615, 15545⟩,
  ⟨11375, .fileSeen, 1427034902867949, 1, 15616, 15545⟩,
  ⟨11376, .fileSeen, 1427034902867949, 1, 15617, 15545⟩,
  ⟨11377, .fileSeen, 1427034902867949, 1, 15618, 15545⟩,
  ⟨11378, .fileSeen, 1427034902867949, 1, 15619, 15545⟩,
  ⟨11379, .fileSeen, 1427034902867949, 1, 15620, 15545⟩,
  ⟨11380, .fileSeen, 1427034902867949, 1, 15621, 15545⟩,
  ⟨11381, .fileSeen, 1427034902867949, 1, 15622, 15545⟩,
  ⟨11382, .fileSeen, 1427034902867949, 1, 15623, 15545⟩,
  ⟨11383, .fileSeen, 1427034902867949, 1, 15624, 15545⟩,
  ⟨11384, .fileSeen, 1427034902867949, 1, 15625, 15545⟩,
  ⟨11385, .fileSeen, 1427034902867949, 1, 15626, 15545⟩,
  ⟨11386, .fileSeen, 1427034902867949, 1, 15627, 15545⟩,
  ⟨11387, .fileSeen, 1427034902867949, 1, 15628, 15545⟩,
  ⟨11388, .fileSeen, 1427034902867949, 1, 15629, 15545⟩,
  ⟨11389, .fileSeen, 1427034902867949, 1, 15630, 15545⟩,
  ⟨11390, .fileSeen, 1427034902867949, 1, 15631, 15545⟩,
  ⟨11391, .fileSeen, 1427034902867949, 1, 15632, 15545⟩,
  ⟨11392, .fileSeen, 1427034902867949, 1, 15633, 15545⟩,
  ⟨11393, .fileSeen, 1427034902867949, 1, 15634, 15545⟩,
  ⟨11394, .fileSeen, 1427034902867949, 1, 15635, 15545⟩,
  ⟨11395, .fileSeen, 1427034902867949, 1, 15636, 15545⟩,
  ⟨11396, .fileSeen, 1427034902867949, 1, 15637, 15545⟩,
  ⟨11397, .fileSeen, 1427034902867949, 1, 15638, 15545⟩,
  ⟨11398, .fileSeen, 1427034902867949, 1, 15639, 15545⟩,
  ⟨11399, .fileSeen, 1427034902867949, 1, 15640, 15545⟩,
  ⟨11400, .fileSeen, 1427034902867949, 1, 15641, 15545⟩,
  ⟨11401, .fileSeen, 1427034902867949, 1, 15642, 15545⟩,
  ⟨11402, .fileSeen, 1427034902867949, 1, 15643, 15545⟩,
  ⟨11403, .fileSeen, 1427034902867949, 1, 15644, 15545⟩,
  ⟨11404, .fileSeen, 1427034902867949, 1, 15645, 15545⟩,
  ⟨11405, .fileSeen, 1427034902867949, 1, 15646, 15545⟩,
  ⟨11406, .fileSeen, 1427034902867949, 1, 15647, 15545⟩,
  ⟨11407, .fileSeen, 1427034902867949, 1, 15648, 15545⟩,
  ⟨11408, .fileSeen, 1427034902867949, 1, 15649, 15545⟩,
  ⟨11409, .fileSeen, 1427034902867949, 1, 15650, 15545⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11370) (.both (Sets.fileRecorded 11371) (.both (Sets.fileRecorded 11372) (.both (Sets.fileRecorded 11373) (.both (Sets.fileRecorded 11374) (.both (Sets.fileRecorded 11375) (.both (Sets.fileRecorded 11376) (.both (Sets.fileRecorded 11377) (.both (Sets.fileRecorded 11378) (.both (Sets.fileRecorded 11379) (.both (Sets.fileRecorded 11380) (.both (Sets.fileRecorded 11381) (.both (Sets.fileRecorded 11382) (.both (Sets.fileRecorded 11383) (.both (Sets.fileRecorded 11384) (.both (Sets.fileRecorded 11385) (.both (Sets.fileRecorded 11386) (.both (Sets.fileRecorded 11387) (.both (Sets.fileRecorded 11388) (.both (Sets.fileRecorded 11389) (.both (Sets.fileRecorded 11390) (.both (Sets.fileRecorded 11391) (.both (Sets.fileRecorded 11392) (.both (Sets.fileRecorded 11393) (.both (Sets.fileRecorded 11394) (.both (Sets.fileRecorded 11395) (.both (Sets.fileRecorded 11396) (.both (Sets.fileRecorded 11397) (.both (Sets.fileRecorded 11398) (.both (Sets.fileRecorded 11399) (.both (Sets.fileRecorded 11400) (.both (Sets.fileRecorded 11401) (.both (Sets.fileRecorded 11402) (.both (Sets.fileRecorded 11403) (.both (Sets.fileRecorded 11404) (.both (Sets.fileRecorded 11405) (.both (Sets.fileRecorded 11406) (.both (Sets.fileRecorded 11407) (.both (Sets.fileRecorded 11408) (Sets.fileRecorded 11409)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M300

#print axioms Cert.M300.verified
