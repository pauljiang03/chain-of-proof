import ChainOfProof
open ChainOfProof

namespace Cert.M322

def cited : List Fact := [
  ⟨12250, .fileSeen, 1427143127764000, 1, 16053, 15339⟩,
  ⟨12251, .fileSeen, 1427143131289266, 1, 16053, 15339⟩,
  ⟨12252, .fileSeen, 1427143279000000, 1, 16054, 15339⟩,
  ⟨12253, .fileSeen, 1427143282214265, 1, 16054, 15339⟩,
  ⟨12254, .fileSeen, 1427143298327579, 1, 16054, 15339⟩,
  ⟨12255, .fileSeen, 1427143427512480, 1, 1269, 15339⟩,
  ⟨12256, .fileSeen, 1427143427622981, 1, 1269, 15339⟩,
  ⟨12257, .fileSeen, 1427143430358490, 1, 1337, 15339⟩,
  ⟨12258, .fileSeen, 1427143430374090, 1, 1337, 15339⟩,
  ⟨12259, .fileSeen, 1427143432457705, 1, 1272, 15339⟩,
  ⟨12260, .fileSeen, 1427143432477705, 1, 1272, 15339⟩,
  ⟨12261, .fileSeen, 1427143497831177, 1, 1293, 15339⟩,
  ⟨12262, .fileSeen, 1427143518426208, 1, 1293, 15339⟩,
  ⟨12263, .fileSeen, 1427143522234227, 1, 1297, 15339⟩,
  ⟨12264, .fileSeen, 1427143522254227, 1, 1297, 15339⟩,
  ⟨12265, .fileSeen, 1427143530127248, 1, 1302, 15339⟩,
  ⟨12266, .fileSeen, 1427143546134771, 1, 1302, 15339⟩,
  ⟨12267, .fileSeen, 1427143675974972, 1, 16038, 15453⟩,
  ⟨12268, .fileSeen, 1427143675994972, 1, 16039, 15453⟩,
  ⟨12269, .fileSeen, 1427143676774973, 1, 16036, 15453⟩,
  ⟨12270, .fileSeen, 1427144026618464, 1, 1311, 15339⟩,
  ⟨12271, .fileSeen, 1427144108521079, 1, 1313, 15339⟩,
  ⟨12272, .fileSeen, 1427144108613082, 1, 1311, 15339⟩,
  ⟨12273, .fileSeen, 1427144108613082, 1, 1313, 15339⟩,
  ⟨12274, .fileSeen, 1427144110333085, 1, 1314, 15339⟩,
  ⟨12275, .fileSeen, 1427144117465595, 1, 1316, 15339⟩,
  ⟨12276, .fileSeen, 1427144117475595, 1, 1316, 15339⟩,
  ⟨12277, .fileSeen, 1427144117490595, 1, 1314, 15339⟩,
  ⟨12278, .fileSeen, 1427144118330597, 1, 1317, 15339⟩,
  ⟨12279, .fileSeen, 1427144129240612, 1, 1319, 15339⟩,
  ⟨12280, .fileSeen, 1427144129250612, 1, 1317, 15339⟩,
  ⟨12281, .fileSeen, 1427144154787650, 1, 1321, 15339⟩,
  ⟨12282, .fileSeen, 1427144154822650, 1, 1319, 15339⟩,
  ⟨12283, .fileSeen, 1427144156134654, 1, 1322, 15339⟩,
  ⟨12284, .fileSeen, 1427144156144654, 1, 1321, 15339⟩,
  ⟨12285, .fileSeen, 1427144157412156, 1, 1323, 15339⟩,
  ⟨12286, .fileSeen, 1427144157422156, 1, 1322, 15339⟩,
  ⟨12287, .fileSeen, 1427144158742158, 1, 1324, 15339⟩,
  ⟨12288, .fileSeen, 1427144158752158, 1, 1323, 15339⟩,
  ⟨12289, .fileSeen, 1427144168707174, 1, 1326, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12250) (.both (Sets.fileRecorded 12251) (.both (Sets.fileRecorded 12252) (.both (Sets.fileRecorded 12253) (.both (Sets.fileRecorded 12254) (.both (Sets.fileRecorded 12255) (.both (Sets.fileRecorded 12256) (.both (Sets.fileRecorded 12257) (.both (Sets.fileRecorded 12258) (.both (Sets.fileRecorded 12259) (.both (Sets.fileRecorded 12260) (.both (Sets.fileRecorded 12261) (.both (Sets.fileRecorded 12262) (.both (Sets.fileRecorded 12263) (.both (Sets.fileRecorded 12264) (.both (Sets.fileRecorded 12265) (.both (Sets.fileRecorded 12266) (.both (Sets.fileRecorded 12267) (.both (Sets.fileRecorded 12268) (.both (Sets.fileRecorded 12269) (.both (Sets.fileRecorded 12270) (.both (Sets.fileRecorded 12271) (.both (Sets.fileRecorded 12272) (.both (Sets.fileRecorded 12273) (.both (Sets.fileRecorded 12274) (.both (Sets.fileRecorded 12275) (.both (Sets.fileRecorded 12276) (.both (Sets.fileRecorded 12277) (.both (Sets.fileRecorded 12278) (.both (Sets.fileRecorded 12279) (.both (Sets.fileRecorded 12280) (.both (Sets.fileRecorded 12281) (.both (Sets.fileRecorded 12282) (.both (Sets.fileRecorded 12283) (.both (Sets.fileRecorded 12284) (.both (Sets.fileRecorded 12285) (.both (Sets.fileRecorded 12286) (.both (Sets.fileRecorded 12287) (.both (Sets.fileRecorded 12288) (Sets.fileRecorded 12289)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M322

#print axioms Cert.M322.verified
