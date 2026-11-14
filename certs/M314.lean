import ChainOfProof
open ChainOfProof

namespace Cert.M314

def cited : List Fact := [
  ⟨11930, .fileSeen, 1427039757290262, 1, 15961, 15339⟩,
  ⟨11931, .fileSeen, 1427039757321462, 1, 1457, 15339⟩,
  ⟨11932, .fileSeen, 1427039757337062, 1, 15962, 15453⟩,
  ⟨11933, .fileSeen, 1427039757337062, 1, 15962, 15339⟩,
  ⟨11934, .fileSeen, 1427039757352662, 1, 15963, 15339⟩,
  ⟨11935, .fileSeen, 1427039757383862, 1, 15964, 15339⟩,
  ⟨11936, .fileSeen, 1427039757383862, 1, 15965, 15339⟩,
  ⟨11937, .fileSeen, 1427039757399462, 1, 15966, 15339⟩,
  ⟨11938, .fileSeen, 1427039757446262, 1, 15952, 15339⟩,
  ⟨11939, .fileSeen, 1427039757446262, 1, 15967, 15339⟩,
  ⟨11940, .fileSeen, 1427039758195063, 1, 15952, 15339⟩,
  ⟨11941, .fileSeen, 1427039760160667, 1, 15968, 15339⟩,
  ⟨11942, .fileSeen, 1427039760160667, 1, 15969, 15339⟩,
  ⟨11943, .fileSeen, 1427039760191867, 1, 15968, 15339⟩,
  ⟨11944, .fileSeen, 1427039760191867, 1, 15970, 15339⟩,
  ⟨11945, .fileSeen, 1427039760238667, 1, 15970, 15339⟩,
  ⟨11946, .fileSeen, 1427039762282271, 1, 15953, 15339⟩,
  ⟨11947, .fileSeen, 1427039762282271, 1, 15971, 15339⟩,
  ⟨11948, .fileSeen, 1427039762282271, 1, 15972, 15339⟩,
  ⟨11949, .fileSeen, 1427039762282271, 1, 15958, 15339⟩,
  ⟨11950, .fileSeen, 1427039762282271, 1, 15973, 15339⟩,
  ⟨11951, .fileSeen, 1427039762282271, 1, 15959, 15339⟩,
  ⟨11952, .fileSeen, 1427039762282271, 1, 15974, 15339⟩,
  ⟨11953, .fileSeen, 1427039762297871, 1, 15956, 15339⟩,
  ⟨11954, .fileSeen, 1427039762297871, 1, 15975, 15339⟩,
  ⟨11955, .fileSeen, 1427039762297871, 1, 15957, 15339⟩,
  ⟨11956, .fileSeen, 1427039762297871, 1, 15976, 15339⟩,
  ⟨11957, .fileSeen, 1427039762313471, 1, 15977, 15339⟩,
  ⟨11958, .fileSeen, 1427039762313471, 1, 15978, 15339⟩,
  ⟨11959, .fileSeen, 1427039762329071, 1, 1458, 15339⟩,
  ⟨11960, .fileSeen, 1427039762329071, 1, 15979, 15339⟩,
  ⟨11961, .fileSeen, 1427039762360271, 1, 15980, 15339⟩,
  ⟨11962, .fileSeen, 1427039762360271, 1, 15961, 15339⟩,
  ⟨11963, .fileSeen, 1427039762360271, 1, 15981, 15339⟩,
  ⟨11964, .fileSeen, 1427039762360271, 1, 15982, 15339⟩,
  ⟨11965, .fileSeen, 1427039762375871, 1, 15955, 15339⟩,
  ⟨11966, .fileSeen, 1427039762375871, 1, 15983, 15339⟩,
  ⟨11967, .fileSeen, 1427039762375871, 1, 15984, 15339⟩,
  ⟨11968, .fileSeen, 1427039762375871, 1, 15985, 15339⟩,
  ⟨11969, .fileSeen, 1427039762375871, 1, 15977, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11930) (.both (Sets.fileRecorded 11931) (.both (Sets.fileRecorded 11932) (.both (Sets.fileRecorded 11933) (.both (Sets.fileRecorded 11934) (.both (Sets.fileRecorded 11935) (.both (Sets.fileRecorded 11936) (.both (Sets.fileRecorded 11937) (.both (Sets.fileRecorded 11938) (.both (Sets.fileRecorded 11939) (.both (Sets.fileRecorded 11940) (.both (Sets.fileRecorded 11941) (.both (Sets.fileRecorded 11942) (.both (Sets.fileRecorded 11943) (.both (Sets.fileRecorded 11944) (.both (Sets.fileRecorded 11945) (.both (Sets.fileRecorded 11946) (.both (Sets.fileRecorded 11947) (.both (Sets.fileRecorded 11948) (.both (Sets.fileRecorded 11949) (.both (Sets.fileRecorded 11950) (.both (Sets.fileRecorded 11951) (.both (Sets.fileRecorded 11952) (.both (Sets.fileRecorded 11953) (.both (Sets.fileRecorded 11954) (.both (Sets.fileRecorded 11955) (.both (Sets.fileRecorded 11956) (.both (Sets.fileRecorded 11957) (.both (Sets.fileRecorded 11958) (.both (Sets.fileRecorded 11959) (.both (Sets.fileRecorded 11960) (.both (Sets.fileRecorded 11961) (.both (Sets.fileRecorded 11962) (.both (Sets.fileRecorded 11963) (.both (Sets.fileRecorded 11964) (.both (Sets.fileRecorded 11965) (.both (Sets.fileRecorded 11966) (.both (Sets.fileRecorded 11967) (.both (Sets.fileRecorded 11968) (Sets.fileRecorded 11969)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M314

#print axioms Cert.M314.verified
