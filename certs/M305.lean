import ChainOfProof
open ChainOfProof

namespace Cert.M305

def cited : List Fact := [
  ⟨11570, .fileSeen, 1427034902867949, 1, 15811, 15545⟩,
  ⟨11571, .fileSeen, 1427034902867949, 1, 15812, 15545⟩,
  ⟨11572, .fileSeen, 1427034902867949, 1, 15813, 15545⟩,
  ⟨11573, .fileSeen, 1427034902867949, 1, 15814, 15545⟩,
  ⟨11574, .fileSeen, 1427034902867949, 1, 15815, 15545⟩,
  ⟨11575, .fileSeen, 1427034902867949, 1, 15816, 15545⟩,
  ⟨11576, .fileSeen, 1427034902867949, 1, 15817, 15545⟩,
  ⟨11577, .fileSeen, 1427034902867949, 1, 15818, 15545⟩,
  ⟨11578, .fileSeen, 1427034902867949, 1, 15819, 15545⟩,
  ⟨11579, .fileSeen, 1427034902867949, 1, 15820, 15545⟩,
  ⟨11580, .fileSeen, 1427034902867949, 1, 15821, 15545⟩,
  ⟨11581, .fileSeen, 1427034902867949, 1, 15822, 15545⟩,
  ⟨11582, .fileSeen, 1427034902867949, 1, 15823, 15545⟩,
  ⟨11583, .fileSeen, 1427034902867949, 1, 15824, 15545⟩,
  ⟨11584, .fileSeen, 1427034902867949, 1, 15825, 15545⟩,
  ⟨11585, .fileSeen, 1427034902867949, 1, 15826, 15545⟩,
  ⟨11586, .fileSeen, 1427034902867949, 1, 15827, 15545⟩,
  ⟨11587, .fileSeen, 1427034902867949, 1, 15828, 15545⟩,
  ⟨11588, .fileSeen, 1427034902867949, 1, 15829, 15545⟩,
  ⟨11589, .fileSeen, 1427034902867949, 1, 15830, 15545⟩,
  ⟨11590, .fileSeen, 1427034902867949, 1, 15831, 15545⟩,
  ⟨11591, .fileSeen, 1427034902867949, 1, 15832, 15545⟩,
  ⟨11592, .fileSeen, 1427034902867949, 1, 15833, 15545⟩,
  ⟨11593, .fileSeen, 1427034902867949, 1, 15834, 15545⟩,
  ⟨11594, .fileSeen, 1427034902867949, 1, 15835, 15545⟩,
  ⟨11595, .fileSeen, 1427034902867949, 1, 15836, 15545⟩,
  ⟨11596, .fileSeen, 1427034902867949, 1, 15837, 15545⟩,
  ⟨11597, .fileSeen, 1427034902867949, 1, 15838, 15545⟩,
  ⟨11598, .fileSeen, 1427034902867949, 1, 15839, 15545⟩,
  ⟨11599, .fileSeen, 1427034902867949, 1, 15840, 15545⟩,
  ⟨11600, .fileSeen, 1427034902930348, 1, 15489, 15339⟩,
  ⟨11601, .fileSeen, 1427034902930348, 1, 15841, 15339⟩,
  ⟨11602, .fileSeen, 1427034903039549, 1, 15842, 15339⟩,
  ⟨11603, .fileSeen, 1427034903039549, 1, 15843, 15339⟩,
  ⟨11604, .fileSeen, 1427034903086349, 1, 15841, 15339⟩,
  ⟨11605, .fileSeen, 1427034903086349, 1, 15844, 15339⟩,
  ⟨11606, .fileSeen, 1427034903101949, 1, 15841, 15339⟩,
  ⟨11607, .fileSeen, 1427034903101949, 1, 15843, 15339⟩,
  ⟨11608, .fileSeen, 1427034906462355, 1, 15519, 15339⟩,
  ⟨11609, .fileSeen, 1427034906477955, 1, 15843, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11570) (.both (Sets.fileRecorded 11571) (.both (Sets.fileRecorded 11572) (.both (Sets.fileRecorded 11573) (.both (Sets.fileRecorded 11574) (.both (Sets.fileRecorded 11575) (.both (Sets.fileRecorded 11576) (.both (Sets.fileRecorded 11577) (.both (Sets.fileRecorded 11578) (.both (Sets.fileRecorded 11579) (.both (Sets.fileRecorded 11580) (.both (Sets.fileRecorded 11581) (.both (Sets.fileRecorded 11582) (.both (Sets.fileRecorded 11583) (.both (Sets.fileRecorded 11584) (.both (Sets.fileRecorded 11585) (.both (Sets.fileRecorded 11586) (.both (Sets.fileRecorded 11587) (.both (Sets.fileRecorded 11588) (.both (Sets.fileRecorded 11589) (.both (Sets.fileRecorded 11590) (.both (Sets.fileRecorded 11591) (.both (Sets.fileRecorded 11592) (.both (Sets.fileRecorded 11593) (.both (Sets.fileRecorded 11594) (.both (Sets.fileRecorded 11595) (.both (Sets.fileRecorded 11596) (.both (Sets.fileRecorded 11597) (.both (Sets.fileRecorded 11598) (.both (Sets.fileRecorded 11599) (.both (Sets.fileRecorded 11600) (.both (Sets.fileRecorded 11601) (.both (Sets.fileRecorded 11602) (.both (Sets.fileRecorded 11603) (.both (Sets.fileRecorded 11604) (.both (Sets.fileRecorded 11605) (.both (Sets.fileRecorded 11606) (.both (Sets.fileRecorded 11607) (.both (Sets.fileRecorded 11608) (Sets.fileRecorded 11609)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M305

#print axioms Cert.M305.verified
