import ChainOfProof
open ChainOfProof

namespace Cert.M312

def cited : List Fact := [
  ⟨11850, .fileSeen, 1427039643326544, 1, 15925, 15339⟩,
  ⟨11851, .fileSeen, 1427039643342144, 1, 15928, 15339⟩,
  ⟨11852, .fileSeen, 1427039643342144, 1, 15920, 15339⟩,
  ⟨11853, .fileSeen, 1427039643342144, 1, 15913, 15339⟩,
  ⟨11854, .fileSeen, 1427039643342144, 1, 15914, 15339⟩,
  ⟨11855, .fileSeen, 1427039643342144, 1, 15921, 15339⟩,
  ⟨11856, .fileSeen, 1427039643357744, 1, 15917, 15339⟩,
  ⟨11857, .fileSeen, 1427039643357744, 1, 15912, 15339⟩,
  ⟨11858, .fileSeen, 1427039643357744, 1, 15916, 15339⟩,
  ⟨11859, .fileSeen, 1427039643357744, 1, 15919, 15339⟩,
  ⟨11860, .fileSeen, 1427039644527746, 1, 15929, 15339⟩,
  ⟨11861, .fileSeen, 1427039644543346, 1, 15909, 15339⟩,
  ⟨11862, .fileSeen, 1427039644543346, 1, 15915, 15339⟩,
  ⟨11863, .fileSeen, 1427039644543346, 1, 15922, 15339⟩,
  ⟨11864, .fileSeen, 1427039644902147, 1, 15544, 15545⟩,
  ⟨11865, .fileSeen, 1427039644902147, 1, 15560, 15545⟩,
  ⟨11866, .fileSeen, 1427039644902147, 1, 15930, 15545⟩,
  ⟨11867, .fileSeen, 1427039644902147, 1, 15931, 15545⟩,
  ⟨11868, .fileSeen, 1427039644902147, 1, 15932, 15545⟩,
  ⟨11869, .fileSeen, 1427039644902147, 1, 15933, 15545⟩,
  ⟨11870, .fileSeen, 1427039644902147, 1, 15934, 15545⟩,
  ⟨11871, .fileSeen, 1427039644902147, 1, 15935, 15545⟩,
  ⟨11872, .fileSeen, 1427039644902147, 1, 15614, 15545⟩,
  ⟨11873, .fileSeen, 1427039644902147, 1, 15936, 15545⟩,
  ⟨11874, .fileSeen, 1427039644902147, 1, 15937, 15545⟩,
  ⟨11875, .fileSeen, 1427039644902147, 1, 15938, 15545⟩,
  ⟨11876, .fileSeen, 1427039644902147, 1, 15939, 15545⟩,
  ⟨11877, .fileSeen, 1427039644902147, 1, 15940, 15545⟩,
  ⟨11878, .fileSeen, 1427039644902147, 1, 15941, 15545⟩,
  ⟨11879, .fileSeen, 1427039644902147, 1, 15942, 15545⟩,
  ⟨11880, .fileSeen, 1427039644902147, 1, 15681, 15545⟩,
  ⟨11881, .fileSeen, 1427039644902147, 1, 15943, 15545⟩,
  ⟨11882, .fileSeen, 1427039644902147, 1, 15944, 15545⟩,
  ⟨11883, .fileSeen, 1427039644902147, 1, 15945, 15545⟩,
  ⟨11884, .fileSeen, 1427039644902147, 1, 15946, 15545⟩,
  ⟨11885, .fileSeen, 1427039644902147, 1, 15947, 15545⟩,
  ⟨11886, .fileSeen, 1427039644902147, 1, 15948, 15545⟩,
  ⟨11887, .fileSeen, 1427039644902147, 1, 15949, 15545⟩,
  ⟨11888, .fileSeen, 1427039644902147, 1, 15808, 15545⟩,
  ⟨11889, .fileSeen, 1427039645089349, 1, 15950, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11850) (.both (Sets.fileRecorded 11851) (.both (Sets.fileRecorded 11852) (.both (Sets.fileRecorded 11853) (.both (Sets.fileRecorded 11854) (.both (Sets.fileRecorded 11855) (.both (Sets.fileRecorded 11856) (.both (Sets.fileRecorded 11857) (.both (Sets.fileRecorded 11858) (.both (Sets.fileRecorded 11859) (.both (Sets.fileRecorded 11860) (.both (Sets.fileRecorded 11861) (.both (Sets.fileRecorded 11862) (.both (Sets.fileRecorded 11863) (.both (Sets.fileRecorded 11864) (.both (Sets.fileRecorded 11865) (.both (Sets.fileRecorded 11866) (.both (Sets.fileRecorded 11867) (.both (Sets.fileRecorded 11868) (.both (Sets.fileRecorded 11869) (.both (Sets.fileRecorded 11870) (.both (Sets.fileRecorded 11871) (.both (Sets.fileRecorded 11872) (.both (Sets.fileRecorded 11873) (.both (Sets.fileRecorded 11874) (.both (Sets.fileRecorded 11875) (.both (Sets.fileRecorded 11876) (.both (Sets.fileRecorded 11877) (.both (Sets.fileRecorded 11878) (.both (Sets.fileRecorded 11879) (.both (Sets.fileRecorded 11880) (.both (Sets.fileRecorded 11881) (.both (Sets.fileRecorded 11882) (.both (Sets.fileRecorded 11883) (.both (Sets.fileRecorded 11884) (.both (Sets.fileRecorded 11885) (.both (Sets.fileRecorded 11886) (.both (Sets.fileRecorded 11887) (.both (Sets.fileRecorded 11888) (Sets.fileRecorded 11889)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M312

#print axioms Cert.M312.verified
