import ChainOfProof
open ChainOfProof

namespace Cert.M291

def cited : List Fact := [
  ⟨11010, .fileSeen, 1247549551674540, 1, 15454, 15339⟩,
  ⟨11011, .fileSeen, 1247549551674540, 1, 15455, 15339⟩,
  ⟨11012, .fileSeen, 1247549551674540, 1, 15456, 15339⟩,
  ⟨11013, .fileSeen, 1247549551674540, 1, 15452, 15339⟩,
  ⟨11014, .fileSeen, 1247549551674540, 1, 15457, 15339⟩,
  ⟨11015, .fileSeen, 1247549551674540, 1, 15403, 15339⟩,
  ⟨11016, .fileSeen, 1247549551674540, 1, 13951, 15453⟩,
  ⟨11017, .fileSeen, 1247549551674540, 1, 13951, 15339⟩,
  ⟨11018, .fileSeen, 1247549551674540, 1, 13980, 15453⟩,
  ⟨11019, .fileSeen, 1247549551674540, 1, 13980, 15339⟩,
  ⟨11020, .fileSeen, 1247549551674540, 1, 13997, 15453⟩,
  ⟨11021, .fileSeen, 1247549551674540, 1, 13997, 15339⟩,
  ⟨11022, .fileSeen, 1247549551674540, 1, 14008, 15453⟩,
  ⟨11023, .fileSeen, 1247549551674540, 1, 14008, 15339⟩,
  ⟨11024, .fileSeen, 1247549551674540, 1, 14012, 15453⟩,
  ⟨11025, .fileSeen, 1247549551674540, 1, 14012, 15339⟩,
  ⟨11026, .fileSeen, 1247549551690140, 1, 15458, 15339⟩,
  ⟨11027, .fileSeen, 1247549551705740, 1, 15459, 15339⟩,
  ⟨11028, .fileSeen, 1247549551705740, 1, 15460, 15339⟩,
  ⟨11029, .fileSeen, 1247549551705740, 1, 15461, 15339⟩,
  ⟨11030, .fileSeen, 1247549558522952, 1, 15462, 15339⟩,
  ⟨11031, .fileSeen, 1247549558522952, 1, 15406, 15339⟩,
  ⟨11032, .fileSeen, 1247549558522952, 1, 15402, 15339⟩,
  ⟨11033, .fileSeen, 1247549558522952, 1, 15404, 15339⟩,
  ⟨11034, .fileSeen, 1247549558538552, 1, 15442, 15339⟩,
  ⟨11035, .fileSeen, 1247549558538552, 1, 15463, 15339⟩,
  ⟨11036, .fileSeen, 1247549558788152, 1, 15445, 15339⟩,
  ⟨11037, .fileSeen, 1247549558834952, 1, 15447, 15339⟩,
  ⟨11038, .fileSeen, 1247549558834952, 1, 15404, 15339⟩,
  ⟨11039, .fileSeen, 1247549558834952, 1, 15405, 15339⟩,
  ⟨11040, .fileSeen, 1247549558850552, 1, 15406, 15339⟩,
  ⟨11041, .fileSeen, 1247549558850552, 1, 15448, 15339⟩,
  ⟨11042, .fileSeen, 1247549558850552, 1, 15446, 15339⟩,
  ⟨11043, .fileSeen, 1247549558850552, 1, 15407, 15339⟩,
  ⟨11044, .fileSeen, 1247549558850552, 1, 15449, 15339⟩,
  ⟨11045, .fileSeen, 1247549558850552, 1, 15450, 15339⟩,
  ⟨11046, .fileSeen, 1247549558850552, 1, 15455, 15339⟩,
  ⟨11047, .fileSeen, 1247549558850552, 1, 15451, 15339⟩,
  ⟨11048, .fileSeen, 1247549558850552, 1, 15452, 15339⟩,
  ⟨11049, .fileSeen, 1247549558866152, 1, 15402, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11010) (.both (Sets.fileRecorded 11011) (.both (Sets.fileRecorded 11012) (.both (Sets.fileRecorded 11013) (.both (Sets.fileRecorded 11014) (.both (Sets.fileRecorded 11015) (.both (Sets.fileRecorded 11016) (.both (Sets.fileRecorded 11017) (.both (Sets.fileRecorded 11018) (.both (Sets.fileRecorded 11019) (.both (Sets.fileRecorded 11020) (.both (Sets.fileRecorded 11021) (.both (Sets.fileRecorded 11022) (.both (Sets.fileRecorded 11023) (.both (Sets.fileRecorded 11024) (.both (Sets.fileRecorded 11025) (.both (Sets.fileRecorded 11026) (.both (Sets.fileRecorded 11027) (.both (Sets.fileRecorded 11028) (.both (Sets.fileRecorded 11029) (.both (Sets.fileRecorded 11030) (.both (Sets.fileRecorded 11031) (.both (Sets.fileRecorded 11032) (.both (Sets.fileRecorded 11033) (.both (Sets.fileRecorded 11034) (.both (Sets.fileRecorded 11035) (.both (Sets.fileRecorded 11036) (.both (Sets.fileRecorded 11037) (.both (Sets.fileRecorded 11038) (.both (Sets.fileRecorded 11039) (.both (Sets.fileRecorded 11040) (.both (Sets.fileRecorded 11041) (.both (Sets.fileRecorded 11042) (.both (Sets.fileRecorded 11043) (.both (Sets.fileRecorded 11044) (.both (Sets.fileRecorded 11045) (.both (Sets.fileRecorded 11046) (.both (Sets.fileRecorded 11047) (.both (Sets.fileRecorded 11048) (Sets.fileRecorded 11049)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M291

#print axioms Cert.M291.verified
