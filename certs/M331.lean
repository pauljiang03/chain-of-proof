import ChainOfProof
open ChainOfProof

namespace Cert.M331

def cited : List Fact := [
  ⟨12610, .fileSeen, 1427295447293805, 1, 16060, 15453⟩,
  ⟨12611, .fileSeen, 1427295447293805, 1, 16061, 15453⟩,
  ⟨12612, .fileSeen, 1427295447293805, 1, 16002, 15453⟩,
  ⟨12613, .fileSeen, 1427295447293805, 1, 16095, 15453⟩,
  ⟨12614, .fileSeen, 1427295447293805, 1, 16087, 15453⟩,
  ⟨12615, .fileSeen, 1427295447293805, 1, 16099, 15453⟩,
  ⟨12616, .fileSeen, 1427295447293805, 1, 16098, 15453⟩,
  ⟨12617, .fileSeen, 1427295447293805, 1, 15501, 15453⟩,
  ⟨12618, .fileSeen, 1427295447293805, 1, 15502, 15453⟩,
  ⟨12619, .fileSeen, 1427295447293805, 1, 15862, 15453⟩,
  ⟨12620, .fileSeen, 1427295447293805, 1, 11124, 15453⟩,
  ⟨12621, .fileSeen, 1427295447293805, 1, 15863, 15453⟩,
  ⟨12622, .fileSeen, 1427295447293805, 1, 16096, 15453⟩,
  ⟨12623, .fileSeen, 1427295447293805, 1, 16107, 15453⟩,
  ⟨12624, .fileSeen, 1427295447293805, 1, 16108, 15453⟩,
  ⟨12625, .fileSeen, 1427295447293805, 1, 16109, 15453⟩,
  ⟨12626, .fileSeen, 1427295447293805, 1, 16100, 15453⟩,
  ⟨12627, .fileSeen, 1427295447293805, 1, 16052, 15453⟩,
  ⟨12628, .fileSeen, 1427295447293805, 1, 16086, 15453⟩,
  ⟨12629, .fileSeen, 1427295447293805, 1, 16010, 15453⟩,
  ⟨12630, .fileSeen, 1427295447293805, 1, 16001, 15453⟩,
  ⟨12631, .fileSeen, 1427295447293805, 1, 16097, 15453⟩,
  ⟨12632, .fileSeen, 1427295447293805, 1, 15543, 15453⟩,
  ⟨12633, .fileSeen, 1427295447293805, 1, 16007, 15453⟩,
  ⟨12634, .fileSeen, 1427295447293805, 1, 15845, 15453⟩,
  ⟨12635, .fileSeen, 1427295447293805, 1, 16085, 15453⟩,
  ⟨12636, .fileSeen, 1427295447293805, 1, 963, 15453⟩,
  ⟨12637, .fileSeen, 1427295447293805, 1, 965, 15453⟩,
  ⟨12638, .fileSeen, 1427295447293805, 1, 15547, 15453⟩,
  ⟨12639, .fileSeen, 1427295447293805, 1, 13951, 15453⟩,
  ⟨12640, .fileSeen, 1427295447293805, 1, 13957, 15453⟩,
  ⟨12641, .fileSeen, 1427295447293805, 1, 13965, 15453⟩,
  ⟨12642, .fileSeen, 1427295447293805, 1, 834, 15453⟩,
  ⟨12643, .fileSeen, 1427295447293805, 1, 13980, 15453⟩,
  ⟨12644, .fileSeen, 1427295447293805, 1, 13988, 15453⟩,
  ⟨12645, .fileSeen, 1427295447293805, 1, 13997, 15453⟩,
  ⟨12646, .fileSeen, 1427295447293805, 1, 14008, 15453⟩,
  ⟨12647, .fileSeen, 1427295447293805, 1, 14012, 15453⟩,
  ⟨12648, .fileSeen, 1427295447293805, 1, 16045, 15453⟩,
  ⟨12649, .fileSeen, 1427295447293805, 1, 15484, 15453⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12610) (.both (Sets.fileRecorded 12611) (.both (Sets.fileRecorded 12612) (.both (Sets.fileRecorded 12613) (.both (Sets.fileRecorded 12614) (.both (Sets.fileRecorded 12615) (.both (Sets.fileRecorded 12616) (.both (Sets.fileRecorded 12617) (.both (Sets.fileRecorded 12618) (.both (Sets.fileRecorded 12619) (.both (Sets.fileRecorded 12620) (.both (Sets.fileRecorded 12621) (.both (Sets.fileRecorded 12622) (.both (Sets.fileRecorded 12623) (.both (Sets.fileRecorded 12624) (.both (Sets.fileRecorded 12625) (.both (Sets.fileRecorded 12626) (.both (Sets.fileRecorded 12627) (.both (Sets.fileRecorded 12628) (.both (Sets.fileRecorded 12629) (.both (Sets.fileRecorded 12630) (.both (Sets.fileRecorded 12631) (.both (Sets.fileRecorded 12632) (.both (Sets.fileRecorded 12633) (.both (Sets.fileRecorded 12634) (.both (Sets.fileRecorded 12635) (.both (Sets.fileRecorded 12636) (.both (Sets.fileRecorded 12637) (.both (Sets.fileRecorded 12638) (.both (Sets.fileRecorded 12639) (.both (Sets.fileRecorded 12640) (.both (Sets.fileRecorded 12641) (.both (Sets.fileRecorded 12642) (.both (Sets.fileRecorded 12643) (.both (Sets.fileRecorded 12644) (.both (Sets.fileRecorded 12645) (.both (Sets.fileRecorded 12646) (.both (Sets.fileRecorded 12647) (.both (Sets.fileRecorded 12648) (Sets.fileRecorded 12649)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M331

#print axioms Cert.M331.verified
