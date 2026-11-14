import ChainOfProof
open ChainOfProof

namespace Cert.M298

def cited : List Fact := [
  ⟨11290, .fileSeen, 1427034902867949, 1, 15478, 15545⟩,
  ⟨11291, .fileSeen, 1427034902867949, 1, 15481, 15545⟩,
  ⟨11292, .fileSeen, 1427034902867949, 1, 12642, 15545⟩,
  ⟨11293, .fileSeen, 1427034902867949, 1, 12633, 15545⟩,
  ⟨11294, .fileSeen, 1427034902867949, 1, 12628, 15545⟩,
  ⟨11295, .fileSeen, 1427034902867949, 1, 13125, 15545⟩,
  ⟨11296, .fileSeen, 1427034902867949, 1, 13951, 15545⟩,
  ⟨11297, .fileSeen, 1427034902867949, 1, 13957, 15545⟩,
  ⟨11298, .fileSeen, 1427034902867949, 1, 13965, 15545⟩,
  ⟨11299, .fileSeen, 1427034902867949, 1, 834, 15545⟩,
  ⟨11300, .fileSeen, 1427034902867949, 1, 13980, 15545⟩,
  ⟨11301, .fileSeen, 1427034902867949, 1, 13988, 15545⟩,
  ⟨11302, .fileSeen, 1427034902867949, 1, 13997, 15545⟩,
  ⟨11303, .fileSeen, 1427034902867949, 1, 14008, 15545⟩,
  ⟨11304, .fileSeen, 1427034902867949, 1, 14012, 15545⟩,
  ⟨11305, .fileSeen, 1427034902867949, 1, 889, 15545⟩,
  ⟨11306, .fileSeen, 1427034902867949, 1, 891, 15545⟩,
  ⟨11307, .fileSeen, 1427034902867949, 1, 15548, 15545⟩,
  ⟨11308, .fileSeen, 1427034902867949, 1, 15549, 15545⟩,
  ⟨11309, .fileSeen, 1427034902867949, 1, 15550, 15545⟩,
  ⟨11310, .fileSeen, 1427034902867949, 1, 15551, 15545⟩,
  ⟨11311, .fileSeen, 1427034902867949, 1, 15552, 15545⟩,
  ⟨11312, .fileSeen, 1427034902867949, 1, 15553, 15545⟩,
  ⟨11313, .fileSeen, 1427034902867949, 1, 15554, 15545⟩,
  ⟨11314, .fileSeen, 1427034902867949, 1, 15555, 15545⟩,
  ⟨11315, .fileSeen, 1427034902867949, 1, 15556, 15545⟩,
  ⟨11316, .fileSeen, 1427034902867949, 1, 15557, 15545⟩,
  ⟨11317, .fileSeen, 1427034902867949, 1, 15558, 15545⟩,
  ⟨11318, .fileSeen, 1427034902867949, 1, 15559, 15545⟩,
  ⟨11319, .fileSeen, 1427034902867949, 1, 15560, 15545⟩,
  ⟨11320, .fileSeen, 1427034902867949, 1, 15561, 15545⟩,
  ⟨11321, .fileSeen, 1427034902867949, 1, 15562, 15545⟩,
  ⟨11322, .fileSeen, 1427034902867949, 1, 15563, 15545⟩,
  ⟨11323, .fileSeen, 1427034902867949, 1, 15564, 15545⟩,
  ⟨11324, .fileSeen, 1427034902867949, 1, 15565, 15545⟩,
  ⟨11325, .fileSeen, 1427034902867949, 1, 15566, 15545⟩,
  ⟨11326, .fileSeen, 1427034902867949, 1, 15567, 15545⟩,
  ⟨11327, .fileSeen, 1427034902867949, 1, 15568, 15545⟩,
  ⟨11328, .fileSeen, 1427034902867949, 1, 15569, 15545⟩,
  ⟨11329, .fileSeen, 1427034902867949, 1, 15570, 15545⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11290) (.both (Sets.fileRecorded 11291) (.both (Sets.fileRecorded 11292) (.both (Sets.fileRecorded 11293) (.both (Sets.fileRecorded 11294) (.both (Sets.fileRecorded 11295) (.both (Sets.fileRecorded 11296) (.both (Sets.fileRecorded 11297) (.both (Sets.fileRecorded 11298) (.both (Sets.fileRecorded 11299) (.both (Sets.fileRecorded 11300) (.both (Sets.fileRecorded 11301) (.both (Sets.fileRecorded 11302) (.both (Sets.fileRecorded 11303) (.both (Sets.fileRecorded 11304) (.both (Sets.fileRecorded 11305) (.both (Sets.fileRecorded 11306) (.both (Sets.fileRecorded 11307) (.both (Sets.fileRecorded 11308) (.both (Sets.fileRecorded 11309) (.both (Sets.fileRecorded 11310) (.both (Sets.fileRecorded 11311) (.both (Sets.fileRecorded 11312) (.both (Sets.fileRecorded 11313) (.both (Sets.fileRecorded 11314) (.both (Sets.fileRecorded 11315) (.both (Sets.fileRecorded 11316) (.both (Sets.fileRecorded 11317) (.both (Sets.fileRecorded 11318) (.both (Sets.fileRecorded 11319) (.both (Sets.fileRecorded 11320) (.both (Sets.fileRecorded 11321) (.both (Sets.fileRecorded 11322) (.both (Sets.fileRecorded 11323) (.both (Sets.fileRecorded 11324) (.both (Sets.fileRecorded 11325) (.both (Sets.fileRecorded 11326) (.both (Sets.fileRecorded 11327) (.both (Sets.fileRecorded 11328) (Sets.fileRecorded 11329)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M298

#print axioms Cert.M298.verified
