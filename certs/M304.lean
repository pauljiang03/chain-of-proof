import ChainOfProof
open ChainOfProof

namespace Cert.M304

def cited : List Fact := [
  ⟨11530, .fileSeen, 1427034902867949, 1, 15771, 15545⟩,
  ⟨11531, .fileSeen, 1427034902867949, 1, 15772, 15545⟩,
  ⟨11532, .fileSeen, 1427034902867949, 1, 15773, 15545⟩,
  ⟨11533, .fileSeen, 1427034902867949, 1, 15774, 15545⟩,
  ⟨11534, .fileSeen, 1427034902867949, 1, 15775, 15545⟩,
  ⟨11535, .fileSeen, 1427034902867949, 1, 15776, 15545⟩,
  ⟨11536, .fileSeen, 1427034902867949, 1, 15777, 15545⟩,
  ⟨11537, .fileSeen, 1427034902867949, 1, 15778, 15545⟩,
  ⟨11538, .fileSeen, 1427034902867949, 1, 15779, 15545⟩,
  ⟨11539, .fileSeen, 1427034902867949, 1, 15780, 15545⟩,
  ⟨11540, .fileSeen, 1427034902867949, 1, 15781, 15545⟩,
  ⟨11541, .fileSeen, 1427034902867949, 1, 15782, 15545⟩,
  ⟨11542, .fileSeen, 1427034902867949, 1, 15783, 15545⟩,
  ⟨11543, .fileSeen, 1427034902867949, 1, 15784, 15545⟩,
  ⟨11544, .fileSeen, 1427034902867949, 1, 15785, 15545⟩,
  ⟨11545, .fileSeen, 1427034902867949, 1, 15786, 15545⟩,
  ⟨11546, .fileSeen, 1427034902867949, 1, 15787, 15545⟩,
  ⟨11547, .fileSeen, 1427034902867949, 1, 15788, 15545⟩,
  ⟨11548, .fileSeen, 1427034902867949, 1, 15789, 15545⟩,
  ⟨11549, .fileSeen, 1427034902867949, 1, 15790, 15545⟩,
  ⟨11550, .fileSeen, 1427034902867949, 1, 15791, 15545⟩,
  ⟨11551, .fileSeen, 1427034902867949, 1, 15792, 15545⟩,
  ⟨11552, .fileSeen, 1427034902867949, 1, 15793, 15545⟩,
  ⟨11553, .fileSeen, 1427034902867949, 1, 15794, 15545⟩,
  ⟨11554, .fileSeen, 1427034902867949, 1, 15795, 15545⟩,
  ⟨11555, .fileSeen, 1427034902867949, 1, 15796, 15545⟩,
  ⟨11556, .fileSeen, 1427034902867949, 1, 15797, 15545⟩,
  ⟨11557, .fileSeen, 1427034902867949, 1, 15798, 15545⟩,
  ⟨11558, .fileSeen, 1427034902867949, 1, 15799, 15545⟩,
  ⟨11559, .fileSeen, 1427034902867949, 1, 15800, 15545⟩,
  ⟨11560, .fileSeen, 1427034902867949, 1, 15801, 15545⟩,
  ⟨11561, .fileSeen, 1427034902867949, 1, 15802, 15545⟩,
  ⟨11562, .fileSeen, 1427034902867949, 1, 15803, 15545⟩,
  ⟨11563, .fileSeen, 1427034902867949, 1, 15804, 15545⟩,
  ⟨11564, .fileSeen, 1427034902867949, 1, 15805, 15545⟩,
  ⟨11565, .fileSeen, 1427034902867949, 1, 15806, 15545⟩,
  ⟨11566, .fileSeen, 1427034902867949, 1, 15807, 15545⟩,
  ⟨11567, .fileSeen, 1427034902867949, 1, 15808, 15545⟩,
  ⟨11568, .fileSeen, 1427034902867949, 1, 15809, 15545⟩,
  ⟨11569, .fileSeen, 1427034902867949, 1, 15810, 15545⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11530) (.both (Sets.fileRecorded 11531) (.both (Sets.fileRecorded 11532) (.both (Sets.fileRecorded 11533) (.both (Sets.fileRecorded 11534) (.both (Sets.fileRecorded 11535) (.both (Sets.fileRecorded 11536) (.both (Sets.fileRecorded 11537) (.both (Sets.fileRecorded 11538) (.both (Sets.fileRecorded 11539) (.both (Sets.fileRecorded 11540) (.both (Sets.fileRecorded 11541) (.both (Sets.fileRecorded 11542) (.both (Sets.fileRecorded 11543) (.both (Sets.fileRecorded 11544) (.both (Sets.fileRecorded 11545) (.both (Sets.fileRecorded 11546) (.both (Sets.fileRecorded 11547) (.both (Sets.fileRecorded 11548) (.both (Sets.fileRecorded 11549) (.both (Sets.fileRecorded 11550) (.both (Sets.fileRecorded 11551) (.both (Sets.fileRecorded 11552) (.both (Sets.fileRecorded 11553) (.both (Sets.fileRecorded 11554) (.both (Sets.fileRecorded 11555) (.both (Sets.fileRecorded 11556) (.both (Sets.fileRecorded 11557) (.both (Sets.fileRecorded 11558) (.both (Sets.fileRecorded 11559) (.both (Sets.fileRecorded 11560) (.both (Sets.fileRecorded 11561) (.both (Sets.fileRecorded 11562) (.both (Sets.fileRecorded 11563) (.both (Sets.fileRecorded 11564) (.both (Sets.fileRecorded 11565) (.both (Sets.fileRecorded 11566) (.both (Sets.fileRecorded 11567) (.both (Sets.fileRecorded 11568) (Sets.fileRecorded 11569)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M304

#print axioms Cert.M304.verified
