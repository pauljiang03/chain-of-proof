import ChainOfProof
open ChainOfProof

namespace Cert.M321

def cited : List Fact := [
  ⟨12210, .fileSeen, 1427140913183447, 1, 16022, 15339⟩,
  ⟨12211, .fileSeen, 1427140913184447, 1, 16025, 15339⟩,
  ⟨12212, .fileSeen, 1427140913184447, 1, 16026, 15339⟩,
  ⟨12213, .fileSeen, 1427140913184447, 1, 16027, 15339⟩,
  ⟨12214, .fileSeen, 1427140913200047, 1, 16028, 15339⟩,
  ⟨12215, .fileSeen, 1427140913215647, 1, 16028, 15339⟩,
  ⟨12216, .fileSeen, 1427140913215647, 1, 16029, 15339⟩,
  ⟨12217, .fileSeen, 1427140913387247, 1, 16030, 15339⟩,
  ⟨12218, .fileSeen, 1427140965433600, 1, 16031, 15339⟩,
  ⟨12219, .fileSeen, 1427140965433600, 1, 16032, 15339⟩,
  ⟨12220, .fileSeen, 1427140965433600, 1, 16033, 15339⟩,
  ⟨12221, .fileSeen, 1427140965433600, 1, 16034, 15339⟩,
  ⟨12222, .fileSeen, 1427140965449200, 1, 16031, 15339⟩,
  ⟨12223, .fileSeen, 1427140965449200, 1, 16035, 15339⟩,
  ⟨12224, .fileSeen, 1427140965449200, 1, 16034, 15339⟩,
  ⟨12225, .fileSeen, 1427140965480400, 1, 16031, 15339⟩,
  ⟨12226, .fileSeen, 1427140971002810, 1, 16036, 15453⟩,
  ⟨12227, .fileSeen, 1427140971018410, 1, 16037, 15453⟩,
  ⟨12228, .fileSeen, 1427140971018410, 1, 16038, 15453⟩,
  ⟨12229, .fileSeen, 1427140971174410, 1, 16039, 15453⟩,
  ⟨12230, .fileSeen, 1427140971486411, 1, 16040, 15453⟩,
  ⟨12231, .fileSeen, 1427140971486411, 1, 16041, 15453⟩,
  ⟨12232, .fileSeen, 1427140971486411, 1, 16042, 15453⟩,
  ⟨12233, .fileSeen, 1427140971502011, 1, 16043, 15453⟩,
  ⟨12234, .fileSeen, 1427140971767211, 1, 16044, 15453⟩,
  ⟨12235, .fileSeen, 1427141132218497, 1, 16045, 15453⟩,
  ⟨12236, .fileSeen, 1427141132358898, 1, 16045, 15453⟩,
  ⟨12237, .fileSeen, 1427141132452498, 1, 16046, 15453⟩,
  ⟨12238, .fileSeen, 1427141132561698, 1, 16047, 15339⟩,
  ⟨12239, .fileSeen, 1427141132577298, 1, 15547, 15453⟩,
  ⟨12240, .fileSeen, 1427141132577298, 1, 15547, 15339⟩,
  ⟨12241, .fileSeen, 1427141134934902, 1, 16047, 15339⟩,
  ⟨12242, .fileSeen, 1427141134950502, 1, 15547, 15339⟩,
  ⟨12243, .fileSeen, 1427142413986593, 1, 16048, 1466⟩,
  ⟨12244, .fileSeen, 1427142416078000, 1, 16049, 16009⟩,
  ⟨12245, .fileSeen, 1427142453345068, 1, 16050, 1466⟩,
  ⟨12246, .fileSeen, 1427142457248000, 1, 16051, 16009⟩,
  ⟨12247, .fileSeen, 1427142764465230, 1, 16052, 15453⟩,
  ⟨12248, .fileSeen, 1427142764730430, 1, 16052, 15453⟩,
  ⟨12249, .fileSeen, 1427143080000000, 1, 16053, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12210) (.both (Sets.fileRecorded 12211) (.both (Sets.fileRecorded 12212) (.both (Sets.fileRecorded 12213) (.both (Sets.fileRecorded 12214) (.both (Sets.fileRecorded 12215) (.both (Sets.fileRecorded 12216) (.both (Sets.fileRecorded 12217) (.both (Sets.fileRecorded 12218) (.both (Sets.fileRecorded 12219) (.both (Sets.fileRecorded 12220) (.both (Sets.fileRecorded 12221) (.both (Sets.fileRecorded 12222) (.both (Sets.fileRecorded 12223) (.both (Sets.fileRecorded 12224) (.both (Sets.fileRecorded 12225) (.both (Sets.fileRecorded 12226) (.both (Sets.fileRecorded 12227) (.both (Sets.fileRecorded 12228) (.both (Sets.fileRecorded 12229) (.both (Sets.fileRecorded 12230) (.both (Sets.fileRecorded 12231) (.both (Sets.fileRecorded 12232) (.both (Sets.fileRecorded 12233) (.both (Sets.fileRecorded 12234) (.both (Sets.fileRecorded 12235) (.both (Sets.fileRecorded 12236) (.both (Sets.fileRecorded 12237) (.both (Sets.fileRecorded 12238) (.both (Sets.fileRecorded 12239) (.both (Sets.fileRecorded 12240) (.both (Sets.fileRecorded 12241) (.both (Sets.fileRecorded 12242) (.both (Sets.fileRecorded 12243) (.both (Sets.fileRecorded 12244) (.both (Sets.fileRecorded 12245) (.both (Sets.fileRecorded 12246) (.both (Sets.fileRecorded 12247) (.both (Sets.fileRecorded 12248) (Sets.fileRecorded 12249)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M321

#print axioms Cert.M321.verified
