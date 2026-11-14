import ChainOfProof
open ChainOfProof

namespace Cert.M317

def cited : List Fact := [
  ⟨12050, .fileSeen, 1427039770108089, 1, 15976, 15339⟩,
  ⟨12051, .fileSeen, 1427039770108089, 1, 15978, 15339⟩,
  ⟨12052, .fileSeen, 1427039770123689, 1, 15969, 15339⟩,
  ⟨12053, .fileSeen, 1427039770123689, 1, 15971, 15339⟩,
  ⟨12054, .fileSeen, 1427039770123689, 1, 15973, 15339⟩,
  ⟨12055, .fileSeen, 1427039770123689, 1, 15974, 15339⟩,
  ⟨12056, .fileSeen, 1427039775271698, 1, 15998, 15339⟩,
  ⟨12057, .fileSeen, 1427039818051980, 1, 15964, 15339⟩,
  ⟨12058, .fileSeen, 1427039818051980, 1, 15965, 15339⟩,
  ⟨12059, .fileSeen, 1427039818051980, 1, 15966, 15339⟩,
  ⟨12060, .fileSeen, 1427039818051980, 1, 15962, 15453⟩,
  ⟨12061, .fileSeen, 1427039818051980, 1, 15962, 15339⟩,
  ⟨12062, .fileSeen, 1427039818083180, 1, 15960, 15453⟩,
  ⟨12063, .fileSeen, 1427039818083180, 1, 15960, 15339⟩,
  ⟨12064, .fileSeen, 1427039818083180, 1, 15964, 15339⟩,
  ⟨12065, .fileSeen, 1427039818083180, 1, 15963, 15339⟩,
  ⟨12066, .fileSeen, 1427039818098781, 1, 15960, 15339⟩,
  ⟨12067, .fileSeen, 1427039818098781, 1, 15965, 15339⟩,
  ⟨12068, .fileSeen, 1427039818098781, 1, 15966, 15339⟩,
  ⟨12069, .fileSeen, 1427039818098781, 1, 15962, 15339⟩,
  ⟨12070, .fileSeen, 1427039822497988, 1, 15907, 15339⟩,
  ⟨12071, .fileSeen, 1427039830081810, 1, 15999, 15339⟩,
  ⟨12072, .fileSeen, 1427039850973248, 1, 16000, 1466⟩,
  ⟨12073, .fileSeen, 1427039851020048, 1, 1465, 1466⟩,
  ⟨12074, .fileSeen, 1427039851020048, 1, 16000, 1466⟩,
  ⟨12075, .fileSeen, 1427039861930469, 1, 15891, 15453⟩,
  ⟨12076, .fileSeen, 1427039861930469, 1, 15891, 15339⟩,
  ⟨12077, .fileSeen, 1427039861930469, 1, 15903, 15453⟩,
  ⟨12078, .fileSeen, 1427039861930469, 1, 15903, 15339⟩,
  ⟨12079, .fileSeen, 1427039861946069, 1, 15891, 15339⟩,
  ⟨12080, .fileSeen, 1427039861946069, 1, 15903, 15339⟩,
  ⟨12081, .fileSeen, 1427039874550891, 1, 15847, 15339⟩,
  ⟨12082, .fileSeen, 1427039874597691, 1, 15356, 15339⟩,
  ⟨12083, .fileSeen, 1427039993844301, 1, 16001, 15453⟩,
  ⟨12084, .fileSeen, 1427040006933527, 1, 15355, 15339⟩,
  ⟨12085, .fileSeen, 1427040007733528, 1, 15365, 15339⟩,
  ⟨12086, .fileSeen, 1427131592706480, 1, 1118, 15339⟩,
  ⟨12087, .fileSeen, 1427131653959000, 1, 15859, 15339⟩,
  ⟨12088, .fileSeen, 1427131653959000, 1, 15542, 15339⟩,
  ⟨12089, .fileSeen, 1427131653990000, 1, 15844, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12050) (.both (Sets.fileRecorded 12051) (.both (Sets.fileRecorded 12052) (.both (Sets.fileRecorded 12053) (.both (Sets.fileRecorded 12054) (.both (Sets.fileRecorded 12055) (.both (Sets.fileRecorded 12056) (.both (Sets.fileRecorded 12057) (.both (Sets.fileRecorded 12058) (.both (Sets.fileRecorded 12059) (.both (Sets.fileRecorded 12060) (.both (Sets.fileRecorded 12061) (.both (Sets.fileRecorded 12062) (.both (Sets.fileRecorded 12063) (.both (Sets.fileRecorded 12064) (.both (Sets.fileRecorded 12065) (.both (Sets.fileRecorded 12066) (.both (Sets.fileRecorded 12067) (.both (Sets.fileRecorded 12068) (.both (Sets.fileRecorded 12069) (.both (Sets.fileRecorded 12070) (.both (Sets.fileRecorded 12071) (.both (Sets.fileRecorded 12072) (.both (Sets.fileRecorded 12073) (.both (Sets.fileRecorded 12074) (.both (Sets.fileRecorded 12075) (.both (Sets.fileRecorded 12076) (.both (Sets.fileRecorded 12077) (.both (Sets.fileRecorded 12078) (.both (Sets.fileRecorded 12079) (.both (Sets.fileRecorded 12080) (.both (Sets.fileRecorded 12081) (.both (Sets.fileRecorded 12082) (.both (Sets.fileRecorded 12083) (.both (Sets.fileRecorded 12084) (.both (Sets.fileRecorded 12085) (.both (Sets.fileRecorded 12086) (.both (Sets.fileRecorded 12087) (.both (Sets.fileRecorded 12088) (Sets.fileRecorded 12089)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M317

#print axioms Cert.M317.verified
