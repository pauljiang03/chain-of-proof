import ChainOfProof
open ChainOfProof

namespace Cert.M315

def cited : List Fact := [
  ⟨11970, .fileSeen, 1427039762375871, 1, 15986, 15339⟩,
  ⟨11971, .fileSeen, 1427039763530273, 1, 15987, 15339⟩,
  ⟨11972, .fileSeen, 1427039764575475, 1, 15988, 15339⟩,
  ⟨11973, .fileSeen, 1427039764591075, 1, 15987, 15339⟩,
  ⟨11974, .fileSeen, 1427039764591075, 1, 15989, 15339⟩,
  ⟨11975, .fileSeen, 1427039764669075, 1, 15989, 15339⟩,
  ⟨11976, .fileSeen, 1427039767040279, 1, 15968, 15339⟩,
  ⟨11977, .fileSeen, 1427039767040279, 1, 15969, 15339⟩,
  ⟨11978, .fileSeen, 1427039767040279, 1, 15953, 15339⟩,
  ⟨11979, .fileSeen, 1427039767040279, 1, 15971, 15339⟩,
  ⟨11980, .fileSeen, 1427039767040279, 1, 15972, 15339⟩,
  ⟨11981, .fileSeen, 1427039767040279, 1, 15957, 15339⟩,
  ⟨11982, .fileSeen, 1427039767040279, 1, 15976, 15339⟩,
  ⟨11983, .fileSeen, 1427039767040279, 1, 15958, 15339⟩,
  ⟨11984, .fileSeen, 1427039767040279, 1, 15973, 15339⟩,
  ⟨11985, .fileSeen, 1427039767040279, 1, 15959, 15339⟩,
  ⟨11986, .fileSeen, 1427039767040279, 1, 15974, 15339⟩,
  ⟨11987, .fileSeen, 1427039767055879, 1, 1458, 15339⟩,
  ⟨11988, .fileSeen, 1427039767055879, 1, 15979, 15339⟩,
  ⟨11989, .fileSeen, 1427039767055879, 1, 15977, 15339⟩,
  ⟨11990, .fileSeen, 1427039767055879, 1, 15978, 15339⟩,
  ⟨11991, .fileSeen, 1427039767071479, 1, 15956, 15339⟩,
  ⟨11992, .fileSeen, 1427039767071479, 1, 15975, 15339⟩,
  ⟨11993, .fileSeen, 1427039767087079, 1, 15961, 15339⟩,
  ⟨11994, .fileSeen, 1427039767102679, 1, 15955, 15339⟩,
  ⟨11995, .fileSeen, 1427039767102679, 1, 15983, 15339⟩,
  ⟨11996, .fileSeen, 1427039767102679, 1, 15984, 15339⟩,
  ⟨11997, .fileSeen, 1427039767102679, 1, 15985, 15339⟩,
  ⟨11998, .fileSeen, 1427039767102679, 1, 15980, 15339⟩,
  ⟨11999, .fileSeen, 1427039767102679, 1, 15981, 15339⟩,
  ⟨12000, .fileSeen, 1427039768413080, 1, 15544, 15545⟩,
  ⟨12001, .fileSeen, 1427039768413080, 1, 1458, 15545⟩,
  ⟨12002, .fileSeen, 1427039768413080, 1, 15990, 15545⟩,
  ⟨12003, .fileSeen, 1427039768413080, 1, 15560, 15545⟩,
  ⟨12004, .fileSeen, 1427039768413080, 1, 15991, 15545⟩,
  ⟨12005, .fileSeen, 1427039768413080, 1, 15992, 15545⟩,
  ⟨12006, .fileSeen, 1427039768413080, 1, 15614, 15545⟩,
  ⟨12007, .fileSeen, 1427039768413080, 1, 15993, 15545⟩,
  ⟨12008, .fileSeen, 1427039768413080, 1, 15681, 15545⟩,
  ⟨12009, .fileSeen, 1427039768413080, 1, 15994, 15545⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11970) (.both (Sets.fileRecorded 11971) (.both (Sets.fileRecorded 11972) (.both (Sets.fileRecorded 11973) (.both (Sets.fileRecorded 11974) (.both (Sets.fileRecorded 11975) (.both (Sets.fileRecorded 11976) (.both (Sets.fileRecorded 11977) (.both (Sets.fileRecorded 11978) (.both (Sets.fileRecorded 11979) (.both (Sets.fileRecorded 11980) (.both (Sets.fileRecorded 11981) (.both (Sets.fileRecorded 11982) (.both (Sets.fileRecorded 11983) (.both (Sets.fileRecorded 11984) (.both (Sets.fileRecorded 11985) (.both (Sets.fileRecorded 11986) (.both (Sets.fileRecorded 11987) (.both (Sets.fileRecorded 11988) (.both (Sets.fileRecorded 11989) (.both (Sets.fileRecorded 11990) (.both (Sets.fileRecorded 11991) (.both (Sets.fileRecorded 11992) (.both (Sets.fileRecorded 11993) (.both (Sets.fileRecorded 11994) (.both (Sets.fileRecorded 11995) (.both (Sets.fileRecorded 11996) (.both (Sets.fileRecorded 11997) (.both (Sets.fileRecorded 11998) (.both (Sets.fileRecorded 11999) (.both (Sets.fileRecorded 12000) (.both (Sets.fileRecorded 12001) (.both (Sets.fileRecorded 12002) (.both (Sets.fileRecorded 12003) (.both (Sets.fileRecorded 12004) (.both (Sets.fileRecorded 12005) (.both (Sets.fileRecorded 12006) (.both (Sets.fileRecorded 12007) (.both (Sets.fileRecorded 12008) (Sets.fileRecorded 12009)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M315

#print axioms Cert.M315.verified
