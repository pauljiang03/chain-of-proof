import ChainOfProof
open ChainOfProof

namespace Cert.M308

def cited : List Fact := [
  ⟨11690, .fileSeen, 1427037076000000, 1, 1111, 15339⟩,
  ⟨11691, .fileSeen, 1427037112048820, 1, 15356, 15339⟩,
  ⟨11692, .fileSeen, 1427037112048820, 1, 15860, 15339⟩,
  ⟨11693, .fileSeen, 1427037112048820, 1, 15861, 15339⟩,
  ⟨11694, .fileSeen, 1427037112048820, 1, 15365, 15339⟩,
  ⟨11695, .fileSeen, 1427037112048820, 1, 15544, 15339⟩,
  ⟨11696, .fileSeen, 1427037860808250, 1, 11124, 15453⟩,
  ⟨11697, .fileSeen, 1427037860917451, 1, 15862, 15453⟩,
  ⟨11698, .fileSeen, 1427037860948651, 1, 15863, 15453⟩,
  ⟨11699, .fileSeen, 1427037863834656, 1, 15539, 15339⟩,
  ⟨11700, .fileSeen, 1427037863834656, 1, 15540, 15339⟩,
  ⟨11701, .fileSeen, 1427037868407465, 1, 15539, 15339⟩,
  ⟨11702, .fileSeen, 1427037870638269, 1, 15540, 15339⟩,
  ⟨11703, .fileSeen, 1427039321746572, 1, 15864, 15339⟩,
  ⟨11704, .fileSeen, 1427039323805776, 1, 15864, 15339⟩,
  ⟨11705, .fileSeen, 1427039323852576, 1, 15865, 15339⟩,
  ⟨11706, .fileSeen, 1427039323868176, 1, 15866, 15339⟩,
  ⟨11707, .fileSeen, 1427039323868176, 1, 15867, 15339⟩,
  ⟨11708, .fileSeen, 1427039323868176, 1, 15868, 15339⟩,
  ⟨11709, .fileSeen, 1427039323883776, 1, 15869, 15339⟩,
  ⟨11710, .fileSeen, 1427039323883776, 1, 15870, 15339⟩,
  ⟨11711, .fileSeen, 1427039323883776, 1, 15871, 15339⟩,
  ⟨11712, .fileSeen, 1427039323883776, 1, 15872, 15339⟩,
  ⟨11713, .fileSeen, 1427039323883776, 1, 15873, 15339⟩,
  ⟨11714, .fileSeen, 1427039323899376, 1, 15874, 15339⟩,
  ⟨11715, .fileSeen, 1427039324757377, 1, 15875, 15339⟩,
  ⟨11716, .fileSeen, 1427039324757377, 1, 15874, 15339⟩,
  ⟨11717, .fileSeen, 1427039324757377, 1, 15876, 15339⟩,
  ⟨11718, .fileSeen, 1427039324757377, 1, 15877, 15339⟩,
  ⟨11719, .fileSeen, 1427039324772977, 1, 15878, 15339⟩,
  ⟨11720, .fileSeen, 1427039324772977, 1, 15879, 15339⟩,
  ⟨11721, .fileSeen, 1427039324772977, 1, 15880, 15339⟩,
  ⟨11722, .fileSeen, 1427039324772977, 1, 15881, 15339⟩,
  ⟨11723, .fileSeen, 1427039324788578, 1, 15882, 15339⟩,
  ⟨11724, .fileSeen, 1427039324788578, 1, 15883, 15339⟩,
  ⟨11725, .fileSeen, 1427039324788578, 1, 15884, 15339⟩,
  ⟨11726, .fileSeen, 1427039324788578, 1, 15885, 15339⟩,
  ⟨11727, .fileSeen, 1427039324804178, 1, 15886, 15339⟩,
  ⟨11728, .fileSeen, 1427039324804178, 1, 15887, 15339⟩,
  ⟨11729, .fileSeen, 1427039324804178, 1, 15888, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11690) (.both (Sets.fileRecorded 11691) (.both (Sets.fileRecorded 11692) (.both (Sets.fileRecorded 11693) (.both (Sets.fileRecorded 11694) (.both (Sets.fileRecorded 11695) (.both (Sets.fileRecorded 11696) (.both (Sets.fileRecorded 11697) (.both (Sets.fileRecorded 11698) (.both (Sets.fileRecorded 11699) (.both (Sets.fileRecorded 11700) (.both (Sets.fileRecorded 11701) (.both (Sets.fileRecorded 11702) (.both (Sets.fileRecorded 11703) (.both (Sets.fileRecorded 11704) (.both (Sets.fileRecorded 11705) (.both (Sets.fileRecorded 11706) (.both (Sets.fileRecorded 11707) (.both (Sets.fileRecorded 11708) (.both (Sets.fileRecorded 11709) (.both (Sets.fileRecorded 11710) (.both (Sets.fileRecorded 11711) (.both (Sets.fileRecorded 11712) (.both (Sets.fileRecorded 11713) (.both (Sets.fileRecorded 11714) (.both (Sets.fileRecorded 11715) (.both (Sets.fileRecorded 11716) (.both (Sets.fileRecorded 11717) (.both (Sets.fileRecorded 11718) (.both (Sets.fileRecorded 11719) (.both (Sets.fileRecorded 11720) (.both (Sets.fileRecorded 11721) (.both (Sets.fileRecorded 11722) (.both (Sets.fileRecorded 11723) (.both (Sets.fileRecorded 11724) (.both (Sets.fileRecorded 11725) (.both (Sets.fileRecorded 11726) (.both (Sets.fileRecorded 11727) (.both (Sets.fileRecorded 11728) (Sets.fileRecorded 11729)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M308

#print axioms Cert.M308.verified
