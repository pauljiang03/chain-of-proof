import ChainOfProof
open ChainOfProof

namespace Cert.M299

def cited : List Fact := [
  ⟨11330, .fileSeen, 1427034902867949, 1, 15571, 15545⟩,
  ⟨11331, .fileSeen, 1427034902867949, 1, 15572, 15545⟩,
  ⟨11332, .fileSeen, 1427034902867949, 1, 15573, 15545⟩,
  ⟨11333, .fileSeen, 1427034902867949, 1, 15574, 15545⟩,
  ⟨11334, .fileSeen, 1427034902867949, 1, 15575, 15545⟩,
  ⟨11335, .fileSeen, 1427034902867949, 1, 15576, 15545⟩,
  ⟨11336, .fileSeen, 1427034902867949, 1, 15577, 15545⟩,
  ⟨11337, .fileSeen, 1427034902867949, 1, 15578, 15545⟩,
  ⟨11338, .fileSeen, 1427034902867949, 1, 15579, 15545⟩,
  ⟨11339, .fileSeen, 1427034902867949, 1, 15580, 15545⟩,
  ⟨11340, .fileSeen, 1427034902867949, 1, 15581, 15545⟩,
  ⟨11341, .fileSeen, 1427034902867949, 1, 15582, 15545⟩,
  ⟨11342, .fileSeen, 1427034902867949, 1, 15583, 15545⟩,
  ⟨11343, .fileSeen, 1427034902867949, 1, 15584, 15545⟩,
  ⟨11344, .fileSeen, 1427034902867949, 1, 15585, 15545⟩,
  ⟨11345, .fileSeen, 1427034902867949, 1, 15586, 15545⟩,
  ⟨11346, .fileSeen, 1427034902867949, 1, 15587, 15545⟩,
  ⟨11347, .fileSeen, 1427034902867949, 1, 15588, 15545⟩,
  ⟨11348, .fileSeen, 1427034902867949, 1, 15589, 15545⟩,
  ⟨11349, .fileSeen, 1427034902867949, 1, 15590, 15545⟩,
  ⟨11350, .fileSeen, 1427034902867949, 1, 15591, 15545⟩,
  ⟨11351, .fileSeen, 1427034902867949, 1, 15592, 15545⟩,
  ⟨11352, .fileSeen, 1427034902867949, 1, 15593, 15545⟩,
  ⟨11353, .fileSeen, 1427034902867949, 1, 15594, 15545⟩,
  ⟨11354, .fileSeen, 1427034902867949, 1, 15595, 15545⟩,
  ⟨11355, .fileSeen, 1427034902867949, 1, 15596, 15545⟩,
  ⟨11356, .fileSeen, 1427034902867949, 1, 15597, 15545⟩,
  ⟨11357, .fileSeen, 1427034902867949, 1, 15598, 15545⟩,
  ⟨11358, .fileSeen, 1427034902867949, 1, 15599, 15545⟩,
  ⟨11359, .fileSeen, 1427034902867949, 1, 15600, 15545⟩,
  ⟨11360, .fileSeen, 1427034902867949, 1, 15601, 15545⟩,
  ⟨11361, .fileSeen, 1427034902867949, 1, 15602, 15545⟩,
  ⟨11362, .fileSeen, 1427034902867949, 1, 15603, 15545⟩,
  ⟨11363, .fileSeen, 1427034902867949, 1, 15604, 15545⟩,
  ⟨11364, .fileSeen, 1427034902867949, 1, 15605, 15545⟩,
  ⟨11365, .fileSeen, 1427034902867949, 1, 15606, 15545⟩,
  ⟨11366, .fileSeen, 1427034902867949, 1, 15607, 15545⟩,
  ⟨11367, .fileSeen, 1427034902867949, 1, 15608, 15545⟩,
  ⟨11368, .fileSeen, 1427034902867949, 1, 15609, 15545⟩,
  ⟨11369, .fileSeen, 1427034902867949, 1, 15610, 15545⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11330) (.both (Sets.fileRecorded 11331) (.both (Sets.fileRecorded 11332) (.both (Sets.fileRecorded 11333) (.both (Sets.fileRecorded 11334) (.both (Sets.fileRecorded 11335) (.both (Sets.fileRecorded 11336) (.both (Sets.fileRecorded 11337) (.both (Sets.fileRecorded 11338) (.both (Sets.fileRecorded 11339) (.both (Sets.fileRecorded 11340) (.both (Sets.fileRecorded 11341) (.both (Sets.fileRecorded 11342) (.both (Sets.fileRecorded 11343) (.both (Sets.fileRecorded 11344) (.both (Sets.fileRecorded 11345) (.both (Sets.fileRecorded 11346) (.both (Sets.fileRecorded 11347) (.both (Sets.fileRecorded 11348) (.both (Sets.fileRecorded 11349) (.both (Sets.fileRecorded 11350) (.both (Sets.fileRecorded 11351) (.both (Sets.fileRecorded 11352) (.both (Sets.fileRecorded 11353) (.both (Sets.fileRecorded 11354) (.both (Sets.fileRecorded 11355) (.both (Sets.fileRecorded 11356) (.both (Sets.fileRecorded 11357) (.both (Sets.fileRecorded 11358) (.both (Sets.fileRecorded 11359) (.both (Sets.fileRecorded 11360) (.both (Sets.fileRecorded 11361) (.both (Sets.fileRecorded 11362) (.both (Sets.fileRecorded 11363) (.both (Sets.fileRecorded 11364) (.both (Sets.fileRecorded 11365) (.both (Sets.fileRecorded 11366) (.both (Sets.fileRecorded 11367) (.both (Sets.fileRecorded 11368) (Sets.fileRecorded 11369)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M299

#print axioms Cert.M299.verified
