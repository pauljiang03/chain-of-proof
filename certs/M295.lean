import ChainOfProof
open ChainOfProof

namespace Cert.M295

def cited : List Fact := [
  ⟨11170, .fileSeen, 1427034881651911, 1, 15501, 15453⟩,
  ⟨11171, .fileSeen, 1427034881651911, 1, 15502, 15453⟩,
  ⟨11172, .fileSeen, 1427034882119912, 1, 15491, 15339⟩,
  ⟨11173, .fileSeen, 1427034886815520, 1, 15503, 15339⟩,
  ⟨11174, .fileSeen, 1427034886815520, 1, 15504, 15339⟩,
  ⟨11175, .fileSeen, 1427034887018320, 1, 15503, 15339⟩,
  ⟨11176, .fileSeen, 1427034887018320, 1, 15505, 15339⟩,
  ⟨11177, .fileSeen, 1427034895036734, 1, 15487, 15339⟩,
  ⟨11178, .fileSeen, 1427034895036734, 1, 15506, 15339⟩,
  ⟨11179, .fileSeen, 1427034895052334, 1, 15492, 15339⟩,
  ⟨11180, .fileSeen, 1427034895052334, 1, 15507, 15339⟩,
  ⟨11181, .fileSeen, 1427034895052334, 1, 15486, 15339⟩,
  ⟨11182, .fileSeen, 1427034895052334, 1, 15508, 15339⟩,
  ⟨11183, .fileSeen, 1427034895067934, 1, 15509, 15339⟩,
  ⟨11184, .fileSeen, 1427034895067934, 1, 15494, 15339⟩,
  ⟨11185, .fileSeen, 1427034895067934, 1, 15510, 15339⟩,
  ⟨11186, .fileSeen, 1427034895067934, 1, 15485, 15339⟩,
  ⟨11187, .fileSeen, 1427034895067934, 1, 15511, 15339⟩,
  ⟨11188, .fileSeen, 1427034895145935, 1, 15493, 15339⟩,
  ⟨11189, .fileSeen, 1427034895145935, 1, 15512, 15339⟩,
  ⟨11190, .fileSeen, 1427034895145935, 1, 15513, 15339⟩,
  ⟨11191, .fileSeen, 1427034895145935, 1, 15514, 15339⟩,
  ⟨11192, .fileSeen, 1427034895255135, 1, 15515, 15339⟩,
  ⟨11193, .fileSeen, 1427034895255135, 1, 15488, 15339⟩,
  ⟨11194, .fileSeen, 1427034895255135, 1, 15516, 15339⟩,
  ⟨11195, .fileSeen, 1427034895270735, 1, 15513, 15339⟩,
  ⟨11196, .fileSeen, 1427034895270735, 1, 15517, 15339⟩,
  ⟨11197, .fileSeen, 1427034895270735, 1, 15518, 15339⟩,
  ⟨11198, .fileSeen, 1427034895301935, 1, 15490, 15339⟩,
  ⟨11199, .fileSeen, 1427034895301935, 1, 15519, 15339⟩,
  ⟨11200, .fileSeen, 1427034895301935, 1, 15520, 15339⟩,
  ⟨11201, .fileSeen, 1427034895301935, 1, 15521, 15339⟩,
  ⟨11202, .fileSeen, 1427034897361139, 1, 15522, 15339⟩,
  ⟨11203, .fileSeen, 1427034897361139, 1, 15523, 15339⟩,
  ⟨11204, .fileSeen, 1427034897361139, 1, 15524, 15339⟩,
  ⟨11205, .fileSeen, 1427034897376739, 1, 15525, 15339⟩,
  ⟨11206, .fileSeen, 1427034897376739, 1, 15526, 15339⟩,
  ⟨11207, .fileSeen, 1427034897376739, 1, 15527, 15339⟩,
  ⟨11208, .fileSeen, 1427034897376739, 1, 15528, 15339⟩,
  ⟨11209, .fileSeen, 1427034897376739, 1, 15529, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11170) (.both (Sets.fileRecorded 11171) (.both (Sets.fileRecorded 11172) (.both (Sets.fileRecorded 11173) (.both (Sets.fileRecorded 11174) (.both (Sets.fileRecorded 11175) (.both (Sets.fileRecorded 11176) (.both (Sets.fileRecorded 11177) (.both (Sets.fileRecorded 11178) (.both (Sets.fileRecorded 11179) (.both (Sets.fileRecorded 11180) (.both (Sets.fileRecorded 11181) (.both (Sets.fileRecorded 11182) (.both (Sets.fileRecorded 11183) (.both (Sets.fileRecorded 11184) (.both (Sets.fileRecorded 11185) (.both (Sets.fileRecorded 11186) (.both (Sets.fileRecorded 11187) (.both (Sets.fileRecorded 11188) (.both (Sets.fileRecorded 11189) (.both (Sets.fileRecorded 11190) (.both (Sets.fileRecorded 11191) (.both (Sets.fileRecorded 11192) (.both (Sets.fileRecorded 11193) (.both (Sets.fileRecorded 11194) (.both (Sets.fileRecorded 11195) (.both (Sets.fileRecorded 11196) (.both (Sets.fileRecorded 11197) (.both (Sets.fileRecorded 11198) (.both (Sets.fileRecorded 11199) (.both (Sets.fileRecorded 11200) (.both (Sets.fileRecorded 11201) (.both (Sets.fileRecorded 11202) (.both (Sets.fileRecorded 11203) (.both (Sets.fileRecorded 11204) (.both (Sets.fileRecorded 11205) (.both (Sets.fileRecorded 11206) (.both (Sets.fileRecorded 11207) (.both (Sets.fileRecorded 11208) (Sets.fileRecorded 11209)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M295

#print axioms Cert.M295.verified
