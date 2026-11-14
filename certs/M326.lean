import ChainOfProof
open ChainOfProof

namespace Cert.M326

def cited : List Fact := [
  ⟨12410, .fileSeen, 1427210195021093, 1, 16070, 15339⟩,
  ⟨12411, .fileSeen, 1427210195021093, 1, 16071, 15339⟩,
  ⟨12412, .fileSeen, 1427210195036693, 1, 15381, 15339⟩,
  ⟨12413, .fileSeen, 1427210195036693, 1, 15377, 15339⟩,
  ⟨12414, .fileSeen, 1427210195052293, 1, 15424, 15339⟩,
  ⟨12415, .fileSeen, 1427210195052293, 1, 15387, 15339⟩,
  ⟨12416, .fileSeen, 1427210195052293, 1, 15383, 15339⟩,
  ⟨12417, .fileSeen, 1427210195052293, 1, 15409, 15339⟩,
  ⟨12418, .fileSeen, 1427210195052293, 1, 15388, 15339⟩,
  ⟨12419, .fileSeen, 1427210229581154, 1, 15437, 15339⟩,
  ⟨12420, .fileSeen, 1427210231390757, 1, 15422, 15339⟩,
  ⟨12421, .fileSeen, 1427210235355164, 1, 15438, 15339⟩,
  ⟨12422, .fileSeen, 1427210242655977, 1, 15439, 15339⟩,
  ⟨12423, .fileSeen, 1427210250237590, 1, 15436, 15339⟩,
  ⟨12424, .fileSeen, 1427210254981998, 1, 16072, 15339⟩,
  ⟨12425, .fileSeen, 1427210261237609, 1, 16073, 15339⟩,
  ⟨12426, .fileSeen, 1427210267085421, 1, 16074, 15339⟩,
  ⟨12427, .fileSeen, 1427210271983830, 1, 16075, 15339⟩,
  ⟨12428, .fileSeen, 1427210278005441, 1, 15435, 15339⟩,
  ⟨12429, .fileSeen, 1427210278036641, 1, 15418, 15339⟩,
  ⟨12430, .fileSeen, 1427210286305655, 1, 15421, 15339⟩,
  ⟨12431, .fileSeen, 1427210297087274, 1, 16076, 15339⟩,
  ⟨12432, .fileSeen, 1427210298569277, 1, 15425, 15339⟩,
  ⟨12433, .fileSeen, 1427210298569277, 1, 15431, 15339⟩,
  ⟨12434, .fileSeen, 1427210298584877, 1, 15427, 15339⟩,
  ⟨12435, .fileSeen, 1427210298600477, 1, 15429, 15339⟩,
  ⟨12436, .fileSeen, 1427210303688086, 1, 15417, 15339⟩,
  ⟨12437, .fileSeen, 1427210303688086, 1, 15423, 15339⟩,
  ⟨12438, .fileSeen, 1427210303703686, 1, 15428, 15339⟩,
  ⟨12439, .fileSeen, 1427210303703686, 1, 16077, 15339⟩,
  ⟨12440, .fileSeen, 1427210303719286, 1, 16078, 15339⟩,
  ⟨12441, .fileSeen, 1427210303734886, 1, 15375, 15339⟩,
  ⟨12442, .fileSeen, 1427221750148572, 1, 16079, 15339⟩,
  ⟨12443, .fileSeen, 1427221750171573, 1, 16079, 15339⟩,
  ⟨12444, .fileSeen, 1427221750171573, 1, 16080, 15339⟩,
  ⟨12445, .fileSeen, 1427221750673602, 1, 16079, 15339⟩,
  ⟨12446, .fileSeen, 1427221751494649, 1, 16080, 15339⟩,
  ⟨12447, .fileSeen, 1427221809566000, 1, 16081, 15339⟩,
  ⟨12448, .fileSeen, 1427221809940876, 1, 16082, 15339⟩,
  ⟨12449, .fileSeen, 1427221809956476, 1, 16082, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12410) (.both (Sets.fileRecorded 12411) (.both (Sets.fileRecorded 12412) (.both (Sets.fileRecorded 12413) (.both (Sets.fileRecorded 12414) (.both (Sets.fileRecorded 12415) (.both (Sets.fileRecorded 12416) (.both (Sets.fileRecorded 12417) (.both (Sets.fileRecorded 12418) (.both (Sets.fileRecorded 12419) (.both (Sets.fileRecorded 12420) (.both (Sets.fileRecorded 12421) (.both (Sets.fileRecorded 12422) (.both (Sets.fileRecorded 12423) (.both (Sets.fileRecorded 12424) (.both (Sets.fileRecorded 12425) (.both (Sets.fileRecorded 12426) (.both (Sets.fileRecorded 12427) (.both (Sets.fileRecorded 12428) (.both (Sets.fileRecorded 12429) (.both (Sets.fileRecorded 12430) (.both (Sets.fileRecorded 12431) (.both (Sets.fileRecorded 12432) (.both (Sets.fileRecorded 12433) (.both (Sets.fileRecorded 12434) (.both (Sets.fileRecorded 12435) (.both (Sets.fileRecorded 12436) (.both (Sets.fileRecorded 12437) (.both (Sets.fileRecorded 12438) (.both (Sets.fileRecorded 12439) (.both (Sets.fileRecorded 12440) (.both (Sets.fileRecorded 12441) (.both (Sets.fileRecorded 12442) (.both (Sets.fileRecorded 12443) (.both (Sets.fileRecorded 12444) (.both (Sets.fileRecorded 12445) (.both (Sets.fileRecorded 12446) (.both (Sets.fileRecorded 12447) (.both (Sets.fileRecorded 12448) (Sets.fileRecorded 12449)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M326

#print axioms Cert.M326.verified
