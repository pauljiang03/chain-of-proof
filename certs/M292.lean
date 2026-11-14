import ChainOfProof
open ChainOfProof

namespace Cert.M292

def cited : List Fact := [
  ⟨11050, .fileSeen, 1247549558866152, 1, 15454, 15339⟩,
  ⟨11051, .fileSeen, 1247549558866152, 1, 15456, 15339⟩,
  ⟨11052, .fileSeen, 1247549558866152, 1, 15457, 15339⟩,
  ⟨11053, .fileSeen, 1247549558866152, 1, 15403, 15339⟩,
  ⟨11054, .fileSeen, 1247549558897352, 1, 15459, 15339⟩,
  ⟨11055, .fileSeen, 1247549558897352, 1, 15460, 15339⟩,
  ⟨11056, .fileSeen, 1247549558897352, 1, 15458, 15339⟩,
  ⟨11057, .fileSeen, 1247549558897352, 1, 15461, 15339⟩,
  ⟨11058, .fileSeen, 1247555251056875, 1, 15362, 15339⟩,
  ⟨11059, .fileSeen, 1247555251056875, 1, 15464, 15339⟩,
  ⟨11060, .fileSeen, 1290310830754983, 1, 15423, 15339⟩,
  ⟨11061, .fileSeen, 1290323798348390, 1, 15465, 15339⟩,
  ⟨11062, .fileSeen, 1290323798504645, 1, 15466, 15339⟩,
  ⟨11063, .fileSeen, 1290323798535896, 1, 15467, 15339⟩,
  ⟨11064, .fileSeen, 1290323798535896, 1, 15468, 15339⟩,
  ⟨11065, .fileSeen, 1290323800957849, 1, 15393, 15339⟩,
  ⟨11066, .fileSeen, 1290323806958041, 1, 15469, 15339⟩,
  ⟨11067, .fileSeen, 1290323806958041, 1, 15467, 15339⟩,
  ⟨11068, .fileSeen, 1290323806958041, 1, 15470, 15339⟩,
  ⟨11069, .fileSeen, 1290323806958041, 1, 15364, 15339⟩,
  ⟨11070, .fileSeen, 1290323806958041, 1, 15471, 15339⟩,
  ⟨11071, .fileSeen, 1290323806958041, 1, 15472, 15339⟩,
  ⟨11072, .fileSeen, 1290323806958041, 1, 15466, 15339⟩,
  ⟨11073, .fileSeen, 1290323806958041, 1, 15468, 15339⟩,
  ⟨11074, .fileSeen, 1290323806958041, 1, 15465, 15339⟩,
  ⟨11075, .fileSeen, 1290323832474482, 1, 15471, 15339⟩,
  ⟨11076, .fileSeen, 1290323832474482, 1, 15472, 15339⟩,
  ⟨11077, .fileSeen, 1290324034043432, 1, 15473, 15339⟩,
  ⟨11078, .fileSeen, 1290324034043432, 1, 15474, 15339⟩,
  ⟨11079, .fileSeen, 1290324034043432, 1, 15475, 15339⟩,
  ⟨11080, .fileSeen, 1290324034043432, 1, 15476, 15339⟩,
  ⟨11081, .fileSeen, 1290324059778631, 1, 15464, 15339⟩,
  ⟨11082, .fileSeen, 1417459825724043, 1, 15477, 15339⟩,
  ⟨11083, .fileSeen, 1417541337387637, 1, 15478, 15339⟩,
  ⟨11084, .fileSeen, 1417706690000000, 1, 15479, 15339⟩,
  ⟨11085, .fileSeen, 1417706690000000, 1, 12629, 15339⟩,
  ⟨11086, .fileSeen, 1418746225424225, 1, 15480, 15339⟩,
  ⟨11087, .fileSeen, 1418746226000000, 1, 12631, 15339⟩,
  ⟨11088, .fileSeen, 1418939458000000, 1, 12633, 15339⟩,
  ⟨11089, .fileSeen, 1419018826000000, 1, 12628, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11050) (.both (Sets.fileRecorded 11051) (.both (Sets.fileRecorded 11052) (.both (Sets.fileRecorded 11053) (.both (Sets.fileRecorded 11054) (.both (Sets.fileRecorded 11055) (.both (Sets.fileRecorded 11056) (.both (Sets.fileRecorded 11057) (.both (Sets.fileRecorded 11058) (.both (Sets.fileRecorded 11059) (.both (Sets.fileRecorded 11060) (.both (Sets.fileRecorded 11061) (.both (Sets.fileRecorded 11062) (.both (Sets.fileRecorded 11063) (.both (Sets.fileRecorded 11064) (.both (Sets.fileRecorded 11065) (.both (Sets.fileRecorded 11066) (.both (Sets.fileRecorded 11067) (.both (Sets.fileRecorded 11068) (.both (Sets.fileRecorded 11069) (.both (Sets.fileRecorded 11070) (.both (Sets.fileRecorded 11071) (.both (Sets.fileRecorded 11072) (.both (Sets.fileRecorded 11073) (.both (Sets.fileRecorded 11074) (.both (Sets.fileRecorded 11075) (.both (Sets.fileRecorded 11076) (.both (Sets.fileRecorded 11077) (.both (Sets.fileRecorded 11078) (.both (Sets.fileRecorded 11079) (.both (Sets.fileRecorded 11080) (.both (Sets.fileRecorded 11081) (.both (Sets.fileRecorded 11082) (.both (Sets.fileRecorded 11083) (.both (Sets.fileRecorded 11084) (.both (Sets.fileRecorded 11085) (.both (Sets.fileRecorded 11086) (.both (Sets.fileRecorded 11087) (.both (Sets.fileRecorded 11088) (Sets.fileRecorded 11089)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M292

#print axioms Cert.M292.verified
