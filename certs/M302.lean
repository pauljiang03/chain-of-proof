import ChainOfProof
open ChainOfProof

namespace Cert.M302

def cited : List Fact := [
  ⟨11450, .fileSeen, 1427034902867949, 1, 15691, 15545⟩,
  ⟨11451, .fileSeen, 1427034902867949, 1, 15692, 15545⟩,
  ⟨11452, .fileSeen, 1427034902867949, 1, 15693, 15545⟩,
  ⟨11453, .fileSeen, 1427034902867949, 1, 15694, 15545⟩,
  ⟨11454, .fileSeen, 1427034902867949, 1, 15695, 15545⟩,
  ⟨11455, .fileSeen, 1427034902867949, 1, 15696, 15545⟩,
  ⟨11456, .fileSeen, 1427034902867949, 1, 15697, 15545⟩,
  ⟨11457, .fileSeen, 1427034902867949, 1, 15698, 15545⟩,
  ⟨11458, .fileSeen, 1427034902867949, 1, 15699, 15545⟩,
  ⟨11459, .fileSeen, 1427034902867949, 1, 15700, 15545⟩,
  ⟨11460, .fileSeen, 1427034902867949, 1, 15701, 15545⟩,
  ⟨11461, .fileSeen, 1427034902867949, 1, 15702, 15545⟩,
  ⟨11462, .fileSeen, 1427034902867949, 1, 15703, 15545⟩,
  ⟨11463, .fileSeen, 1427034902867949, 1, 15704, 15545⟩,
  ⟨11464, .fileSeen, 1427034902867949, 1, 15705, 15545⟩,
  ⟨11465, .fileSeen, 1427034902867949, 1, 15706, 15545⟩,
  ⟨11466, .fileSeen, 1427034902867949, 1, 15707, 15545⟩,
  ⟨11467, .fileSeen, 1427034902867949, 1, 15708, 15545⟩,
  ⟨11468, .fileSeen, 1427034902867949, 1, 15709, 15545⟩,
  ⟨11469, .fileSeen, 1427034902867949, 1, 15710, 15545⟩,
  ⟨11470, .fileSeen, 1427034902867949, 1, 15711, 15545⟩,
  ⟨11471, .fileSeen, 1427034902867949, 1, 15712, 15545⟩,
  ⟨11472, .fileSeen, 1427034902867949, 1, 15713, 15545⟩,
  ⟨11473, .fileSeen, 1427034902867949, 1, 15714, 15545⟩,
  ⟨11474, .fileSeen, 1427034902867949, 1, 15715, 15545⟩,
  ⟨11475, .fileSeen, 1427034902867949, 1, 15716, 15545⟩,
  ⟨11476, .fileSeen, 1427034902867949, 1, 15717, 15545⟩,
  ⟨11477, .fileSeen, 1427034902867949, 1, 15718, 15545⟩,
  ⟨11478, .fileSeen, 1427034902867949, 1, 15719, 15545⟩,
  ⟨11479, .fileSeen, 1427034902867949, 1, 15720, 15545⟩,
  ⟨11480, .fileSeen, 1427034902867949, 1, 15721, 15545⟩,
  ⟨11481, .fileSeen, 1427034902867949, 1, 15722, 15545⟩,
  ⟨11482, .fileSeen, 1427034902867949, 1, 15723, 15545⟩,
  ⟨11483, .fileSeen, 1427034902867949, 1, 15724, 15545⟩,
  ⟨11484, .fileSeen, 1427034902867949, 1, 15725, 15545⟩,
  ⟨11485, .fileSeen, 1427034902867949, 1, 15726, 15545⟩,
  ⟨11486, .fileSeen, 1427034902867949, 1, 15727, 15545⟩,
  ⟨11487, .fileSeen, 1427034902867949, 1, 15728, 15545⟩,
  ⟨11488, .fileSeen, 1427034902867949, 1, 15729, 15545⟩,
  ⟨11489, .fileSeen, 1427034902867949, 1, 15730, 15545⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11450) (.both (Sets.fileRecorded 11451) (.both (Sets.fileRecorded 11452) (.both (Sets.fileRecorded 11453) (.both (Sets.fileRecorded 11454) (.both (Sets.fileRecorded 11455) (.both (Sets.fileRecorded 11456) (.both (Sets.fileRecorded 11457) (.both (Sets.fileRecorded 11458) (.both (Sets.fileRecorded 11459) (.both (Sets.fileRecorded 11460) (.both (Sets.fileRecorded 11461) (.both (Sets.fileRecorded 11462) (.both (Sets.fileRecorded 11463) (.both (Sets.fileRecorded 11464) (.both (Sets.fileRecorded 11465) (.both (Sets.fileRecorded 11466) (.both (Sets.fileRecorded 11467) (.both (Sets.fileRecorded 11468) (.both (Sets.fileRecorded 11469) (.both (Sets.fileRecorded 11470) (.both (Sets.fileRecorded 11471) (.both (Sets.fileRecorded 11472) (.both (Sets.fileRecorded 11473) (.both (Sets.fileRecorded 11474) (.both (Sets.fileRecorded 11475) (.both (Sets.fileRecorded 11476) (.both (Sets.fileRecorded 11477) (.both (Sets.fileRecorded 11478) (.both (Sets.fileRecorded 11479) (.both (Sets.fileRecorded 11480) (.both (Sets.fileRecorded 11481) (.both (Sets.fileRecorded 11482) (.both (Sets.fileRecorded 11483) (.both (Sets.fileRecorded 11484) (.both (Sets.fileRecorded 11485) (.both (Sets.fileRecorded 11486) (.both (Sets.fileRecorded 11487) (.both (Sets.fileRecorded 11488) (Sets.fileRecorded 11489)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M302

#print axioms Cert.M302.verified
