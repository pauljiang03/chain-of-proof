import ChainOfProof
open ChainOfProof

namespace Cert.M332

def cited : List Fact := [
  ⟨12650, .fileSeen, 1427295447293805, 1, 15497, 15453⟩,
  ⟨12651, .fileSeen, 1427295447293805, 1, 15960, 15453⟩,
  ⟨12652, .fileSeen, 1427295447293805, 1, 15962, 15453⟩,
  ⟨12653, .fileSeen, 1427297089628000, 1, 13034, 16009⟩,
  ⟨12654, .fileSeen, 1427297313647604, 1, 16101, 1549⟩,
  ⟨12655, .fileSeen, 1427297313647604, 1, 16102, 1549⟩,
  ⟨12656, .fileSeen, 1427297313647604, 1, 16103, 1549⟩,
  ⟨12657, .fileSeen, 1427297313647604, 1, 16084, 1549⟩,
  ⟨12658, .fileSeen, 1427297313647604, 1, 16110, 1549⟩,
  ⟨12659, .fileSeen, 1427297313647604, 1, 16110, 1549⟩,
  ⟨12660, .fileSeen, 1427297313663204, 1, 16111, 1466⟩,
  ⟨12661, .fileSeen, 1427297313850405, 1, 16112, 16113⟩,
  ⟨12662, .fileSeen, 1427297313850405, 1, 16114, 16113⟩,
  ⟨12663, .fileSeen, 1427297314817605, 1, 16112, 16113⟩,
  ⟨12664, .fileSeen, 1427297314817605, 1, 16114, 16113⟩,
  ⟨12665, .fileSeen, 1427297348981604, 1, 16048, 1466⟩,
  ⟨12666, .fileSeen, 1427297348981604, 1, 1540, 1466⟩,
  ⟨12667, .fileSeen, 1427297348981604, 1, 1541, 1466⟩,
  ⟨12668, .fileSeen, 1427297348981604, 1, 16091, 1466⟩,
  ⟨12669, .fileSeen, 1427297348981604, 1, 16092, 1466⟩,
  ⟨12670, .fileSeen, 1427297348981604, 1, 16115, 1466⟩,
  ⟨12671, .fileSeen, 1427297348981604, 1, 16115, 1466⟩,
  ⟨12672, .fileSeen, 1427297348981604, 1, 16111, 1466⟩,
  ⟨12673, .fileSeen, 1427297348981604, 1, 16093, 1466⟩,
  ⟨12674, .fileSeen, 1427297348981604, 1, 16012, 1466⟩,
  ⟨12675, .fileSeen, 1427297348981604, 1, 16050, 1466⟩,
  ⟨12676, .fileSeen, 1427297348981604, 1, 16116, 1466⟩,
  ⟨12677, .fileSeen, 1427297348981604, 1, 16116, 1466⟩,
  ⟨12678, .fileSeen, 1427297348981604, 1, 1542, 1466⟩,
  ⟨12679, .fileSeen, 1427297348981604, 1, 1543, 1466⟩,
  ⟨12680, .fileSeen, 1427297348981604, 1, 1420, 1466⟩,
  ⟨12681, .fileSeen, 1427297348981604, 1, 16090, 1466⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12650) (.both (Sets.fileRecorded 12651) (.both (Sets.fileRecorded 12652) (.both (Sets.fileRecorded 12653) (.both (Sets.fileRecorded 12654) (.both (Sets.fileRecorded 12655) (.both (Sets.fileRecorded 12656) (.both (Sets.fileRecorded 12657) (.both (Sets.fileRecorded 12658) (.both (Sets.fileRecorded 12659) (.both (Sets.fileRecorded 12660) (.both (Sets.fileRecorded 12661) (.both (Sets.fileRecorded 12662) (.both (Sets.fileRecorded 12663) (.both (Sets.fileRecorded 12664) (.both (Sets.fileRecorded 12665) (.both (Sets.fileRecorded 12666) (.both (Sets.fileRecorded 12667) (.both (Sets.fileRecorded 12668) (.both (Sets.fileRecorded 12669) (.both (Sets.fileRecorded 12670) (.both (Sets.fileRecorded 12671) (.both (Sets.fileRecorded 12672) (.both (Sets.fileRecorded 12673) (.both (Sets.fileRecorded 12674) (.both (Sets.fileRecorded 12675) (.both (Sets.fileRecorded 12676) (.both (Sets.fileRecorded 12677) (.both (Sets.fileRecorded 12678) (.both (Sets.fileRecorded 12679) (.both (Sets.fileRecorded 12680) (Sets.fileRecorded 12681)))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M332

#print axioms Cert.M332.verified
