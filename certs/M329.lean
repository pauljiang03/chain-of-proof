import ChainOfProof
open ChainOfProof

namespace Cert.M329

def cited : List Fact := [
  ⟨12530, .fileSeen, 1427278692075945, 1, 16069, 15339⟩,
  ⟨12531, .fileSeen, 1427278692122745, 1, 16077, 15339⟩,
  ⟨12532, .fileSeen, 1427278692185145, 1, 16064, 15339⟩,
  ⟨12533, .fileSeen, 1427278692247545, 1, 15469, 15339⟩,
  ⟨12534, .fileSeen, 1427278692247545, 1, 15467, 15339⟩,
  ⟨12535, .fileSeen, 1427278692247545, 1, 16062, 15339⟩,
  ⟨12536, .fileSeen, 1427278692263145, 1, 15469, 15339⟩,
  ⟨12537, .fileSeen, 1427278692356745, 1, 15357, 15339⟩,
  ⟨12538, .fileSeen, 1427278692356745, 1, 16065, 15339⟩,
  ⟨12539, .fileSeen, 1427278692372345, 1, 16065, 15339⟩,
  ⟨12540, .fileSeen, 1427278692481546, 1, 15357, 15339⟩,
  ⟨12541, .fileSeen, 1427278692481546, 1, 15351, 15339⟩,
  ⟨12542, .fileSeen, 1427278692481546, 1, 16068, 15339⟩,
  ⟨12543, .fileSeen, 1427278694010348, 1, 16074, 15339⟩,
  ⟨12544, .fileSeen, 1427278694025948, 1, 16074, 15339⟩,
  ⟨12545, .fileSeen, 1427278694166349, 1, 16072, 15339⟩,
  ⟨12546, .fileSeen, 1427278694244349, 1, 16075, 15339⟩,
  ⟨12547, .fileSeen, 1427278694259949, 1, 16075, 15339⟩,
  ⟨12548, .fileSeen, 1427278694291149, 1, 16073, 15339⟩,
  ⟨12549, .fileSeen, 1427278694306749, 1, 16073, 15339⟩,
  ⟨12550, .fileSeen, 1427278694618749, 1, 15463, 15339⟩,
  ⟨12551, .fileSeen, 1427278694618749, 1, 16076, 15339⟩,
  ⟨12552, .fileSeen, 1427278694618749, 1, 15461, 15339⟩,
  ⟨12553, .fileSeen, 1427278694634349, 1, 15463, 15339⟩,
  ⟨12554, .fileSeen, 1427278694868350, 1, 15462, 15339⟩,
  ⟨12555, .fileSeen, 1427278694868350, 1, 16070, 15339⟩,
  ⟨12556, .fileSeen, 1427278694868350, 1, 15378, 15339⟩,
  ⟨12557, .fileSeen, 1427278694883950, 1, 16078, 15339⟩,
  ⟨12558, .fileSeen, 1427278694883950, 1, 15393, 15339⟩,
  ⟨12559, .fileSeen, 1427282059892352, 1, 15338, 15339⟩,
  ⟨12560, .fileSeen, 1427294464011005, 1, 16095, 15453⟩,
  ⟨12561, .fileSeen, 1427294464619405, 1, 16096, 15453⟩,
  ⟨12562, .fileSeen, 1427294464635005, 1, 15863, 15453⟩,
  ⟨12563, .fileSeen, 1427294464635005, 1, 16096, 15453⟩,
  ⟨12564, .fileSeen, 1427294470235405, 1, 16097, 15453⟩,
  ⟨12565, .fileSeen, 1427294470251005, 1, 16098, 15453⟩,
  ⟨12566, .fileSeen, 1427294473246205, 1, 16099, 15453⟩,
  ⟨12567, .fileSeen, 1427294766397005, 1, 16100, 15453⟩,
  ⟨12568, .fileSeen, 1427294850593705, 1, 11124, 15453⟩,
  ⟨12569, .fileSeen, 1427294860125305, 1, 963, 15453⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12530) (.both (Sets.fileRecorded 12531) (.both (Sets.fileRecorded 12532) (.both (Sets.fileRecorded 12533) (.both (Sets.fileRecorded 12534) (.both (Sets.fileRecorded 12535) (.both (Sets.fileRecorded 12536) (.both (Sets.fileRecorded 12537) (.both (Sets.fileRecorded 12538) (.both (Sets.fileRecorded 12539) (.both (Sets.fileRecorded 12540) (.both (Sets.fileRecorded 12541) (.both (Sets.fileRecorded 12542) (.both (Sets.fileRecorded 12543) (.both (Sets.fileRecorded 12544) (.both (Sets.fileRecorded 12545) (.both (Sets.fileRecorded 12546) (.both (Sets.fileRecorded 12547) (.both (Sets.fileRecorded 12548) (.both (Sets.fileRecorded 12549) (.both (Sets.fileRecorded 12550) (.both (Sets.fileRecorded 12551) (.both (Sets.fileRecorded 12552) (.both (Sets.fileRecorded 12553) (.both (Sets.fileRecorded 12554) (.both (Sets.fileRecorded 12555) (.both (Sets.fileRecorded 12556) (.both (Sets.fileRecorded 12557) (.both (Sets.fileRecorded 12558) (.both (Sets.fileRecorded 12559) (.both (Sets.fileRecorded 12560) (.both (Sets.fileRecorded 12561) (.both (Sets.fileRecorded 12562) (.both (Sets.fileRecorded 12563) (.both (Sets.fileRecorded 12564) (.both (Sets.fileRecorded 12565) (.both (Sets.fileRecorded 12566) (.both (Sets.fileRecorded 12567) (.both (Sets.fileRecorded 12568) (Sets.fileRecorded 12569)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M329

#print axioms Cert.M329.verified
