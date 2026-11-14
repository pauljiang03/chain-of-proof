import ChainOfProof
open ChainOfProof

namespace Cert.M319

def cited : List Fact := [
  ⟨12130, .fileSeen, 1427131685610869, 1, 15536, 15339⟩,
  ⟨12131, .fileSeen, 1427131685626469, 1, 15538, 15339⟩,
  ⟨12132, .fileSeen, 1427131685642069, 1, 15537, 15339⟩,
  ⟨12133, .fileSeen, 1427131685642069, 1, 1118, 15339⟩,
  ⟨12134, .fileSeen, 1427131685688869, 1, 1096, 15339⟩,
  ⟨12135, .fileSeen, 1427131698700305, 1, 1115, 15339⟩,
  ⟨12136, .fileSeen, 1427131698731505, 1, 1115, 15339⟩,
  ⟨12137, .fileSeen, 1427131767000000, 1, 16004, 15339⟩,
  ⟨12138, .fileSeen, 1427131769181071, 1, 16004, 15339⟩,
  ⟨12139, .fileSeen, 1427134072314187, 1, 1160, 15339⟩,
  ⟨12140, .fileSeen, 1427134072334187, 1, 1160, 15339⟩,
  ⟨12141, .fileSeen, 1427134074981192, 1, 1161, 15339⟩,
  ⟨12142, .fileSeen, 1427134077949700, 1, 1161, 15339⟩,
  ⟨12143, .fileSeen, 1427134078080701, 1, 1164, 15339⟩,
  ⟨12144, .fileSeen, 1427134079890207, 1, 1165, 15339⟩,
  ⟨12145, .fileSeen, 1427134096983258, 1, 16005, 15453⟩,
  ⟨12146, .fileSeen, 1427134096983258, 1, 16006, 15453⟩,
  ⟨12147, .fileSeen, 1427134097103258, 1, 16005, 15453⟩,
  ⟨12148, .fileSeen, 1427134097103258, 1, 16006, 15453⟩,
  ⟨12149, .fileSeen, 1427134098133259, 1, 1169, 15339⟩,
  ⟨12150, .fileSeen, 1427134098143259, 1, 1164, 15339⟩,
  ⟨12151, .fileSeen, 1427134098143259, 1, 1165, 15339⟩,
  ⟨12152, .fileSeen, 1427134263021023, 1, 1169, 15339⟩,
  ⟨12153, .fileSeen, 1427134272889588, 1, 1188, 15339⟩,
  ⟨12154, .fileSeen, 1427134321722211, 1, 1188, 15339⟩,
  ⟨12155, .fileSeen, 1427134327649223, 1, 1196, 15339⟩,
  ⟨12156, .fileSeen, 1427134327659223, 1, 1196, 15339⟩,
  ⟨12157, .fileSeen, 1427134365477284, 1, 1201, 15339⟩,
  ⟨12158, .fileSeen, 1427134365507284, 1, 1201, 15339⟩,
  ⟨12159, .fileSeen, 1427134372241296, 1, 1202, 15339⟩,
  ⟨12160, .fileSeen, 1427134377881309, 1, 1202, 15339⟩,
  ⟨12161, .fileSeen, 1427134437502906, 1, 1207, 15339⟩,
  ⟨12162, .fileSeen, 1427134437522906, 1, 1207, 15339⟩,
  ⟨12163, .fileSeen, 1427134464652450, 1, 1210, 15339⟩,
  ⟨12164, .fileSeen, 1427134473644462, 1, 1210, 15339⟩,
  ⟨12165, .fileSeen, 1427135827457633, 1, 16007, 15453⟩,
  ⟨12166, .fileSeen, 1427135874476000, 1, 16008, 16009⟩,
  ⟨12167, .fileSeen, 1427135874491716, 1, 16010, 15453⟩,
  ⟨12168, .fileSeen, 1427135880000000, 60000000, 16008, 16011⟩,
  ⟨12169, .fileSeen, 1427135891386545, 1, 16008, 16011⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12130) (.both (Sets.fileRecorded 12131) (.both (Sets.fileRecorded 12132) (.both (Sets.fileRecorded 12133) (.both (Sets.fileRecorded 12134) (.both (Sets.fileRecorded 12135) (.both (Sets.fileRecorded 12136) (.both (Sets.fileRecorded 12137) (.both (Sets.fileRecorded 12138) (.both (Sets.fileRecorded 12139) (.both (Sets.fileRecorded 12140) (.both (Sets.fileRecorded 12141) (.both (Sets.fileRecorded 12142) (.both (Sets.fileRecorded 12143) (.both (Sets.fileRecorded 12144) (.both (Sets.fileRecorded 12145) (.both (Sets.fileRecorded 12146) (.both (Sets.fileRecorded 12147) (.both (Sets.fileRecorded 12148) (.both (Sets.fileRecorded 12149) (.both (Sets.fileRecorded 12150) (.both (Sets.fileRecorded 12151) (.both (Sets.fileRecorded 12152) (.both (Sets.fileRecorded 12153) (.both (Sets.fileRecorded 12154) (.both (Sets.fileRecorded 12155) (.both (Sets.fileRecorded 12156) (.both (Sets.fileRecorded 12157) (.both (Sets.fileRecorded 12158) (.both (Sets.fileRecorded 12159) (.both (Sets.fileRecorded 12160) (.both (Sets.fileRecorded 12161) (.both (Sets.fileRecorded 12162) (.both (Sets.fileRecorded 12163) (.both (Sets.fileRecorded 12164) (.both (Sets.fileRecorded 12165) (.both (Sets.fileRecorded 12166) (.both (Sets.fileRecorded 12167) (.both (Sets.fileRecorded 12168) (Sets.fileRecorded 12169)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M319

#print axioms Cert.M319.verified
