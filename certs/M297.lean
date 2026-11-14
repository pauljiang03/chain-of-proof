import ChainOfProof
open ChainOfProof

namespace Cert.M297

def cited : List Fact := [
  ⟨11250, .fileSeen, 1427034899903943, 1, 15490, 15339⟩,
  ⟨11251, .fileSeen, 1427034899903943, 1, 15519, 15339⟩,
  ⟨11252, .fileSeen, 1427034899903943, 1, 15520, 15339⟩,
  ⟨11253, .fileSeen, 1427034899903943, 1, 15515, 15339⟩,
  ⟨11254, .fileSeen, 1427034902353147, 1, 15543, 15453⟩,
  ⟨11255, .fileSeen, 1427034902446747, 1, 15513, 15339⟩,
  ⟨11256, .fileSeen, 1427034902462347, 1, 15503, 15339⟩,
  ⟨11257, .fileSeen, 1427034902462347, 1, 15492, 15339⟩,
  ⟨11258, .fileSeen, 1427034902462347, 1, 15494, 15339⟩,
  ⟨11259, .fileSeen, 1427034902477948, 1, 15493, 15339⟩,
  ⟨11260, .fileSeen, 1427034902493548, 1, 15490, 15339⟩,
  ⟨11261, .fileSeen, 1427034902509148, 1, 15485, 15339⟩,
  ⟨11262, .fileSeen, 1427034902509148, 1, 15486, 15339⟩,
  ⟨11263, .fileSeen, 1427034902509148, 1, 15487, 15339⟩,
  ⟨11264, .fileSeen, 1427034902509148, 1, 15488, 15339⟩,
  ⟨11265, .fileSeen, 1427034902867949, 1, 15544, 15545⟩,
  ⟨11266, .fileSeen, 1427034902867949, 1, 15406, 15545⟩,
  ⟨11267, .fileSeen, 1427034902867949, 1, 15448, 15545⟩,
  ⟨11268, .fileSeen, 1427034902867949, 1, 15446, 15545⟩,
  ⟨11269, .fileSeen, 1427034902867949, 1, 15447, 15545⟩,
  ⟨11270, .fileSeen, 1427034902867949, 1, 15402, 15545⟩,
  ⟨11271, .fileSeen, 1427034902867949, 1, 15454, 15545⟩,
  ⟨11272, .fileSeen, 1427034902867949, 1, 15449, 15545⟩,
  ⟨11273, .fileSeen, 1427034902867949, 1, 15450, 15545⟩,
  ⟨11274, .fileSeen, 1427034902867949, 1, 15455, 15545⟩,
  ⟨11275, .fileSeen, 1427034902867949, 1, 15451, 15545⟩,
  ⟨11276, .fileSeen, 1427034902867949, 1, 15456, 15545⟩,
  ⟨11277, .fileSeen, 1427034902867949, 1, 15452, 15545⟩,
  ⟨11278, .fileSeen, 1427034902867949, 1, 15457, 15545⟩,
  ⟨11279, .fileSeen, 1427034902867949, 1, 15404, 15545⟩,
  ⟨11280, .fileSeen, 1427034902867949, 1, 15445, 15545⟩,
  ⟨11281, .fileSeen, 1427034902867949, 1, 15546, 15545⟩,
  ⟨11282, .fileSeen, 1427034902867949, 1, 833, 15545⟩,
  ⟨11283, .fileSeen, 1427034902867949, 1, 15547, 15545⟩,
  ⟨11284, .fileSeen, 1427034902867949, 1, 13034, 15545⟩,
  ⟨11285, .fileSeen, 1427034902867949, 1, 15480, 15545⟩,
  ⟨11286, .fileSeen, 1427034902867949, 1, 12630, 15545⟩,
  ⟨11287, .fileSeen, 1427034902867949, 1, 12631, 15545⟩,
  ⟨11288, .fileSeen, 1427034902867949, 1, 15482, 15545⟩,
  ⟨11289, .fileSeen, 1427034902867949, 1, 15477, 15545⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11250) (.both (Sets.fileRecorded 11251) (.both (Sets.fileRecorded 11252) (.both (Sets.fileRecorded 11253) (.both (Sets.fileRecorded 11254) (.both (Sets.fileRecorded 11255) (.both (Sets.fileRecorded 11256) (.both (Sets.fileRecorded 11257) (.both (Sets.fileRecorded 11258) (.both (Sets.fileRecorded 11259) (.both (Sets.fileRecorded 11260) (.both (Sets.fileRecorded 11261) (.both (Sets.fileRecorded 11262) (.both (Sets.fileRecorded 11263) (.both (Sets.fileRecorded 11264) (.both (Sets.fileRecorded 11265) (.both (Sets.fileRecorded 11266) (.both (Sets.fileRecorded 11267) (.both (Sets.fileRecorded 11268) (.both (Sets.fileRecorded 11269) (.both (Sets.fileRecorded 11270) (.both (Sets.fileRecorded 11271) (.both (Sets.fileRecorded 11272) (.both (Sets.fileRecorded 11273) (.both (Sets.fileRecorded 11274) (.both (Sets.fileRecorded 11275) (.both (Sets.fileRecorded 11276) (.both (Sets.fileRecorded 11277) (.both (Sets.fileRecorded 11278) (.both (Sets.fileRecorded 11279) (.both (Sets.fileRecorded 11280) (.both (Sets.fileRecorded 11281) (.both (Sets.fileRecorded 11282) (.both (Sets.fileRecorded 11283) (.both (Sets.fileRecorded 11284) (.both (Sets.fileRecorded 11285) (.both (Sets.fileRecorded 11286) (.both (Sets.fileRecorded 11287) (.both (Sets.fileRecorded 11288) (Sets.fileRecorded 11289)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M297

#print axioms Cert.M297.verified
