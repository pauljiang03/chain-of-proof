import ChainOfProof
open ChainOfProof

namespace Cert.M318

def cited : List Fact := [
  ⟨12090, .fileSeen, 1427131653990000, 1, 15842, 15339⟩,
  ⟨12091, .fileSeen, 1427131654021000, 1, 15523, 15339⟩,
  ⟨12092, .fileSeen, 1427131654021000, 1, 15524, 15339⟩,
  ⟨12093, .fileSeen, 1427131654021000, 1, 15529, 15339⟩,
  ⟨12094, .fileSeen, 1427131654021000, 1, 15530, 15339⟩,
  ⟨12095, .fileSeen, 1427131654021000, 1, 15541, 15339⟩,
  ⟨12096, .fileSeen, 1427131654723000, 1, 15531, 15339⟩,
  ⟨12097, .fileSeen, 1427131654754000, 1, 15532, 15339⟩,
  ⟨12098, .fileSeen, 1427131654785000, 1, 15533, 15339⟩,
  ⟨12099, .fileSeen, 1427131654785000, 1, 15526, 15339⟩,
  ⟨12100, .fileSeen, 1427131654801000, 1, 15527, 15339⟩,
  ⟨12101, .fileSeen, 1427131654801000, 1, 15528, 15339⟩,
  ⟨12102, .fileSeen, 1427131654817000, 1, 15535, 15339⟩,
  ⟨12103, .fileSeen, 1427131654817000, 1, 15536, 15339⟩,
  ⟨12104, .fileSeen, 1427131654817000, 1, 15537, 15339⟩,
  ⟨12105, .fileSeen, 1427131654817000, 1, 15538, 15339⟩,
  ⟨12106, .fileSeen, 1427131659918391, 1, 16002, 15453⟩,
  ⟨12107, .fileSeen, 1427131669150805, 1, 1129, 15339⟩,
  ⟨12108, .fileSeen, 1427131669338005, 1, 1130, 15339⟩,
  ⟨12109, .fileSeen, 1427131669353605, 1, 1094, 15339⟩,
  ⟨12110, .fileSeen, 1427131679701911, 1, 1094, 15339⟩,
  ⟨12111, .fileSeen, 1427131680184930, 1, 16003, 15339⟩,
  ⟨12112, .fileSeen, 1427131680216130, 1, 1130, 15339⟩,
  ⟨12113, .fileSeen, 1427131680216130, 1, 1129, 15339⟩,
  ⟨12114, .fileSeen, 1427131682163190, 1, 15859, 15339⟩,
  ⟨12115, .fileSeen, 1427131682993021, 1, 15844, 15339⟩,
  ⟨12116, .fileSeen, 1427131683052025, 1, 15842, 15339⟩,
  ⟨12117, .fileSeen, 1427131683080026, 1, 15542, 15339⟩,
  ⟨12118, .fileSeen, 1427131683131029, 1, 15541, 15339⟩,
  ⟨12119, .fileSeen, 1427131683176032, 1, 15531, 15339⟩,
  ⟨12120, .fileSeen, 1427131683971448, 1, 15532, 15339⟩,
  ⟨12121, .fileSeen, 1427131683994449, 1, 15533, 15339⟩,
  ⟨12122, .fileSeen, 1427131684022451, 1, 15528, 15339⟩,
  ⟨12123, .fileSeen, 1427131685454869, 1, 15526, 15339⟩,
  ⟨12124, .fileSeen, 1427131685470469, 1, 15527, 15339⟩,
  ⟨12125, .fileSeen, 1427131685501669, 1, 15530, 15339⟩,
  ⟨12126, .fileSeen, 1427131685517269, 1, 15529, 15339⟩,
  ⟨12127, .fileSeen, 1427131685532869, 1, 15523, 15339⟩,
  ⟨12128, .fileSeen, 1427131685564069, 1, 15524, 15339⟩,
  ⟨12129, .fileSeen, 1427131685579669, 1, 15535, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12090) (.both (Sets.fileRecorded 12091) (.both (Sets.fileRecorded 12092) (.both (Sets.fileRecorded 12093) (.both (Sets.fileRecorded 12094) (.both (Sets.fileRecorded 12095) (.both (Sets.fileRecorded 12096) (.both (Sets.fileRecorded 12097) (.both (Sets.fileRecorded 12098) (.both (Sets.fileRecorded 12099) (.both (Sets.fileRecorded 12100) (.both (Sets.fileRecorded 12101) (.both (Sets.fileRecorded 12102) (.both (Sets.fileRecorded 12103) (.both (Sets.fileRecorded 12104) (.both (Sets.fileRecorded 12105) (.both (Sets.fileRecorded 12106) (.both (Sets.fileRecorded 12107) (.both (Sets.fileRecorded 12108) (.both (Sets.fileRecorded 12109) (.both (Sets.fileRecorded 12110) (.both (Sets.fileRecorded 12111) (.both (Sets.fileRecorded 12112) (.both (Sets.fileRecorded 12113) (.both (Sets.fileRecorded 12114) (.both (Sets.fileRecorded 12115) (.both (Sets.fileRecorded 12116) (.both (Sets.fileRecorded 12117) (.both (Sets.fileRecorded 12118) (.both (Sets.fileRecorded 12119) (.both (Sets.fileRecorded 12120) (.both (Sets.fileRecorded 12121) (.both (Sets.fileRecorded 12122) (.both (Sets.fileRecorded 12123) (.both (Sets.fileRecorded 12124) (.both (Sets.fileRecorded 12125) (.both (Sets.fileRecorded 12126) (.both (Sets.fileRecorded 12127) (.both (Sets.fileRecorded 12128) (Sets.fileRecorded 12129)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M318

#print axioms Cert.M318.verified
