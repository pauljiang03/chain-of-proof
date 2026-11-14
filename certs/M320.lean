import ChainOfProof
open ChainOfProof

namespace Cert.M320

def cited : List Fact := [
  ⟨12170, .fileSeen, 1427135901230162, 1, 16012, 1466⟩,
  ⟨12171, .fileSeen, 1427135903398000, 1, 16013, 16009⟩,
  ⟨12172, .fileSeen, 1427135975158693, 1, 15479, 15339⟩,
  ⟨12173, .fileSeen, 1427136240000000, 1, 16014, 15339⟩,
  ⟨12174, .fileSeen, 1427136271719000, 1, 16014, 15339⟩,
  ⟨12175, .fileSeen, 1427136275813333, 1, 16004, 15339⟩,
  ⟨12176, .fileSeen, 1427136276820227, 1, 16004, 15339⟩,
  ⟨12177, .fileSeen, 1427136278250914, 1, 16014, 15339⟩,
  ⟨12178, .fileSeen, 1427136280096233, 1, 16014, 15339⟩,
  ⟨12179, .fileSeen, 1427138098000000, 1, 16015, 15339⟩,
  ⟨12180, .fileSeen, 1427138100258496, 1, 16015, 15339⟩,
  ⟨12181, .fileSeen, 1427138340000000, 1, 16016, 15339⟩,
  ⟨12182, .fileSeen, 1427138340000000, 1, 15479, 15339⟩,
  ⟨12183, .fileSeen, 1427138362086000, 1, 16016, 15339⟩,
  ⟨12184, .fileSeen, 1427138362086000, 1, 15479, 15339⟩,
  ⟨12185, .fileSeen, 1427138365495735, 1, 16015, 15339⟩,
  ⟨12186, .fileSeen, 1427138375808716, 1, 16016, 15339⟩,
  ⟨12187, .fileSeen, 1427138441000000, 1, 16017, 15339⟩,
  ⟨12188, .fileSeen, 1427138441921166, 1, 16017, 15339⟩,
  ⟨12189, .fileSeen, 1427138441921167, 1, 16017, 15339⟩,
  ⟨12190, .fileSeen, 1427138529927413, 1, 16017, 15339⟩,
  ⟨12191, .fileSeen, 1427138782000000, 1, 16018, 15339⟩,
  ⟨12192, .fileSeen, 1427138783855622, 1, 16018, 15339⟩,
  ⟨12193, .fileSeen, 1427138820000000, 1, 16019, 15339⟩,
  ⟨12194, .fileSeen, 1427138825282000, 1, 16019, 15339⟩,
  ⟨12195, .fileSeen, 1427138828638351, 1, 16019, 15339⟩,
  ⟨12196, .fileSeen, 1427138904186761, 1, 16018, 15339⟩,
  ⟨12197, .fileSeen, 1427140547296776, 1, 891, 15339⟩,
  ⟨12198, .fileSeen, 1427140590661442, 1, 889, 15339⟩,
  ⟨12199, .fileSeen, 1427140593481297, 1, 889, 15339⟩,
  ⟨12200, .fileSeen, 1427140593496897, 1, 889, 15339⟩,
  ⟨12201, .fileSeen, 1427140613339270, 1, 891, 15339⟩,
  ⟨12202, .fileSeen, 1427140613354870, 1, 891, 15339⟩,
  ⟨12203, .fileSeen, 1427140650515000, 1, 16020, 15339⟩,
  ⟨12204, .fileSeen, 1427140660733292, 1, 16020, 15339⟩,
  ⟨12205, .fileSeen, 1427140860012550, 1, 16021, 15339⟩,
  ⟨12206, .fileSeen, 1427140913135647, 1, 16022, 15339⟩,
  ⟨12207, .fileSeen, 1427140913151247, 1, 16023, 15339⟩,
  ⟨12208, .fileSeen, 1427140913166847, 1, 16024, 15339⟩,
  ⟨12209, .fileSeen, 1427140913166847, 1, 16023, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12170) (.both (Sets.fileRecorded 12171) (.both (Sets.fileRecorded 12172) (.both (Sets.fileRecorded 12173) (.both (Sets.fileRecorded 12174) (.both (Sets.fileRecorded 12175) (.both (Sets.fileRecorded 12176) (.both (Sets.fileRecorded 12177) (.both (Sets.fileRecorded 12178) (.both (Sets.fileRecorded 12179) (.both (Sets.fileRecorded 12180) (.both (Sets.fileRecorded 12181) (.both (Sets.fileRecorded 12182) (.both (Sets.fileRecorded 12183) (.both (Sets.fileRecorded 12184) (.both (Sets.fileRecorded 12185) (.both (Sets.fileRecorded 12186) (.both (Sets.fileRecorded 12187) (.both (Sets.fileRecorded 12188) (.both (Sets.fileRecorded 12189) (.both (Sets.fileRecorded 12190) (.both (Sets.fileRecorded 12191) (.both (Sets.fileRecorded 12192) (.both (Sets.fileRecorded 12193) (.both (Sets.fileRecorded 12194) (.both (Sets.fileRecorded 12195) (.both (Sets.fileRecorded 12196) (.both (Sets.fileRecorded 12197) (.both (Sets.fileRecorded 12198) (.both (Sets.fileRecorded 12199) (.both (Sets.fileRecorded 12200) (.both (Sets.fileRecorded 12201) (.both (Sets.fileRecorded 12202) (.both (Sets.fileRecorded 12203) (.both (Sets.fileRecorded 12204) (.both (Sets.fileRecorded 12205) (.both (Sets.fileRecorded 12206) (.both (Sets.fileRecorded 12207) (.both (Sets.fileRecorded 12208) (Sets.fileRecorded 12209)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M320

#print axioms Cert.M320.verified
