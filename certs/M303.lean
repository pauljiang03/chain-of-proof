import ChainOfProof
open ChainOfProof

namespace Cert.M303

def cited : List Fact := [
  ⟨11490, .fileSeen, 1427034902867949, 1, 15731, 15545⟩,
  ⟨11491, .fileSeen, 1427034902867949, 1, 15732, 15545⟩,
  ⟨11492, .fileSeen, 1427034902867949, 1, 15733, 15545⟩,
  ⟨11493, .fileSeen, 1427034902867949, 1, 15734, 15545⟩,
  ⟨11494, .fileSeen, 1427034902867949, 1, 15735, 15545⟩,
  ⟨11495, .fileSeen, 1427034902867949, 1, 15736, 15545⟩,
  ⟨11496, .fileSeen, 1427034902867949, 1, 15737, 15545⟩,
  ⟨11497, .fileSeen, 1427034902867949, 1, 15738, 15545⟩,
  ⟨11498, .fileSeen, 1427034902867949, 1, 15739, 15545⟩,
  ⟨11499, .fileSeen, 1427034902867949, 1, 15740, 15545⟩,
  ⟨11500, .fileSeen, 1427034902867949, 1, 15741, 15545⟩,
  ⟨11501, .fileSeen, 1427034902867949, 1, 15742, 15545⟩,
  ⟨11502, .fileSeen, 1427034902867949, 1, 15743, 15545⟩,
  ⟨11503, .fileSeen, 1427034902867949, 1, 15744, 15545⟩,
  ⟨11504, .fileSeen, 1427034902867949, 1, 15745, 15545⟩,
  ⟨11505, .fileSeen, 1427034902867949, 1, 15746, 15545⟩,
  ⟨11506, .fileSeen, 1427034902867949, 1, 15747, 15545⟩,
  ⟨11507, .fileSeen, 1427034902867949, 1, 15748, 15545⟩,
  ⟨11508, .fileSeen, 1427034902867949, 1, 15749, 15545⟩,
  ⟨11509, .fileSeen, 1427034902867949, 1, 15750, 15545⟩,
  ⟨11510, .fileSeen, 1427034902867949, 1, 15751, 15545⟩,
  ⟨11511, .fileSeen, 1427034902867949, 1, 15752, 15545⟩,
  ⟨11512, .fileSeen, 1427034902867949, 1, 15753, 15545⟩,
  ⟨11513, .fileSeen, 1427034902867949, 1, 15754, 15545⟩,
  ⟨11514, .fileSeen, 1427034902867949, 1, 15755, 15545⟩,
  ⟨11515, .fileSeen, 1427034902867949, 1, 15756, 15545⟩,
  ⟨11516, .fileSeen, 1427034902867949, 1, 15757, 15545⟩,
  ⟨11517, .fileSeen, 1427034902867949, 1, 15758, 15545⟩,
  ⟨11518, .fileSeen, 1427034902867949, 1, 15759, 15545⟩,
  ⟨11519, .fileSeen, 1427034902867949, 1, 15760, 15545⟩,
  ⟨11520, .fileSeen, 1427034902867949, 1, 15761, 15545⟩,
  ⟨11521, .fileSeen, 1427034902867949, 1, 15762, 15545⟩,
  ⟨11522, .fileSeen, 1427034902867949, 1, 15763, 15545⟩,
  ⟨11523, .fileSeen, 1427034902867949, 1, 15764, 15545⟩,
  ⟨11524, .fileSeen, 1427034902867949, 1, 15765, 15545⟩,
  ⟨11525, .fileSeen, 1427034902867949, 1, 15766, 15545⟩,
  ⟨11526, .fileSeen, 1427034902867949, 1, 15767, 15545⟩,
  ⟨11527, .fileSeen, 1427034902867949, 1, 15768, 15545⟩,
  ⟨11528, .fileSeen, 1427034902867949, 1, 15769, 15545⟩,
  ⟨11529, .fileSeen, 1427034902867949, 1, 15770, 15545⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11490) (.both (Sets.fileRecorded 11491) (.both (Sets.fileRecorded 11492) (.both (Sets.fileRecorded 11493) (.both (Sets.fileRecorded 11494) (.both (Sets.fileRecorded 11495) (.both (Sets.fileRecorded 11496) (.both (Sets.fileRecorded 11497) (.both (Sets.fileRecorded 11498) (.both (Sets.fileRecorded 11499) (.both (Sets.fileRecorded 11500) (.both (Sets.fileRecorded 11501) (.both (Sets.fileRecorded 11502) (.both (Sets.fileRecorded 11503) (.both (Sets.fileRecorded 11504) (.both (Sets.fileRecorded 11505) (.both (Sets.fileRecorded 11506) (.both (Sets.fileRecorded 11507) (.both (Sets.fileRecorded 11508) (.both (Sets.fileRecorded 11509) (.both (Sets.fileRecorded 11510) (.both (Sets.fileRecorded 11511) (.both (Sets.fileRecorded 11512) (.both (Sets.fileRecorded 11513) (.both (Sets.fileRecorded 11514) (.both (Sets.fileRecorded 11515) (.both (Sets.fileRecorded 11516) (.both (Sets.fileRecorded 11517) (.both (Sets.fileRecorded 11518) (.both (Sets.fileRecorded 11519) (.both (Sets.fileRecorded 11520) (.both (Sets.fileRecorded 11521) (.both (Sets.fileRecorded 11522) (.both (Sets.fileRecorded 11523) (.both (Sets.fileRecorded 11524) (.both (Sets.fileRecorded 11525) (.both (Sets.fileRecorded 11526) (.both (Sets.fileRecorded 11527) (.both (Sets.fileRecorded 11528) (Sets.fileRecorded 11529)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M303

#print axioms Cert.M303.verified
