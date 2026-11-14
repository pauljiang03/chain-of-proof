import ChainOfProof
open ChainOfProof

namespace Cert.M328

def cited : List Fact := [
  ⟨12490, .fileSeen, 1427226766832162, 1, 13988, 15339⟩,
  ⟨12491, .fileSeen, 1427226766832162, 1, 13997, 15453⟩,
  ⟨12492, .fileSeen, 1427226766832162, 1, 13997, 15339⟩,
  ⟨12493, .fileSeen, 1427226766847762, 1, 14008, 15453⟩,
  ⟨12494, .fileSeen, 1427226766847762, 1, 14008, 15339⟩,
  ⟨12495, .fileSeen, 1427226766847762, 1, 14012, 15453⟩,
  ⟨12496, .fileSeen, 1427226766847762, 1, 14012, 15339⟩,
  ⟨12497, .fileSeen, 1427227281338079, 1, 13951, 15339⟩,
  ⟨12498, .fileSeen, 1427227281353679, 1, 14012, 15339⟩,
  ⟨12499, .fileSeen, 1427227281369279, 1, 14008, 15339⟩,
  ⟨12500, .fileSeen, 1427227281384879, 1, 13997, 15339⟩,
  ⟨12501, .fileSeen, 1427227281400479, 1, 13988, 15339⟩,
  ⟨12502, .fileSeen, 1427227281416079, 1, 13980, 15339⟩,
  ⟨12503, .fileSeen, 1427227281431679, 1, 13965, 15339⟩,
  ⟨12504, .fileSeen, 1427227281447280, 1, 13957, 15339⟩,
  ⟨12505, .fileSeen, 1427227281447280, 1, 834, 15339⟩,
  ⟨12506, .fileSeen, 1427229858901833, 1, 16090, 1466⟩,
  ⟨12507, .fileSeen, 1427230874320000, 1, 15543, 15453⟩,
  ⟨12508, .fileSeen, 1427230874320463, 1, 16091, 1466⟩,
  ⟨12509, .fileSeen, 1427230874320463, 1, 16092, 1466⟩,
  ⟨12510, .fileSeen, 1427230874320463, 1, 16093, 1466⟩,
  ⟨12511, .fileSeen, 1427231100000000, 1, 16094, 15339⟩,
  ⟨12512, .fileSeen, 1427231109679000, 1, 16094, 15339⟩,
  ⟨12513, .fileSeen, 1427231111285000, 1, 16094, 15339⟩,
  ⟨12514, .fileSeen, 1427231112409083, 1, 16094, 15339⟩,
  ⟨12515, .fileSeen, 1427231128757912, 1, 16001, 15453⟩,
  ⟨12516, .fileSeen, 1427231243397713, 1, 15846, 15453⟩,
  ⟨12517, .fileSeen, 1427231244864916, 1, 15862, 15453⟩,
  ⟨12518, .fileSeen, 1427231245613717, 1, 15497, 15339⟩,
  ⟨12519, .fileSeen, 1427231245629318, 1, 15484, 15339⟩,
  ⟨12520, .fileSeen, 1427231246612119, 1, 15484, 15339⟩,
  ⟨12521, .fileSeen, 1427231246612119, 1, 15497, 15339⟩,
  ⟨12522, .fileSeen, 1427278523408449, 1, 15338, 15339⟩,
  ⟨12523, .fileSeen, 1427278523408449, 1, 15340, 15339⟩,
  ⟨12524, .fileSeen, 1427278691327144, 1, 16071, 15339⟩,
  ⟨12525, .fileSeen, 1427278691358344, 1, 16071, 15339⟩,
  ⟨12526, .fileSeen, 1427278691623544, 1, 16067, 15339⟩,
  ⟨12527, .fileSeen, 1427278691826344, 1, 16068, 15339⟩,
  ⟨12528, .fileSeen, 1427278691873144, 1, 16063, 15339⟩,
  ⟨12529, .fileSeen, 1427278691935545, 1, 16066, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12490) (.both (Sets.fileRecorded 12491) (.both (Sets.fileRecorded 12492) (.both (Sets.fileRecorded 12493) (.both (Sets.fileRecorded 12494) (.both (Sets.fileRecorded 12495) (.both (Sets.fileRecorded 12496) (.both (Sets.fileRecorded 12497) (.both (Sets.fileRecorded 12498) (.both (Sets.fileRecorded 12499) (.both (Sets.fileRecorded 12500) (.both (Sets.fileRecorded 12501) (.both (Sets.fileRecorded 12502) (.both (Sets.fileRecorded 12503) (.both (Sets.fileRecorded 12504) (.both (Sets.fileRecorded 12505) (.both (Sets.fileRecorded 12506) (.both (Sets.fileRecorded 12507) (.both (Sets.fileRecorded 12508) (.both (Sets.fileRecorded 12509) (.both (Sets.fileRecorded 12510) (.both (Sets.fileRecorded 12511) (.both (Sets.fileRecorded 12512) (.both (Sets.fileRecorded 12513) (.both (Sets.fileRecorded 12514) (.both (Sets.fileRecorded 12515) (.both (Sets.fileRecorded 12516) (.both (Sets.fileRecorded 12517) (.both (Sets.fileRecorded 12518) (.both (Sets.fileRecorded 12519) (.both (Sets.fileRecorded 12520) (.both (Sets.fileRecorded 12521) (.both (Sets.fileRecorded 12522) (.both (Sets.fileRecorded 12523) (.both (Sets.fileRecorded 12524) (.both (Sets.fileRecorded 12525) (.both (Sets.fileRecorded 12526) (.both (Sets.fileRecorded 12527) (.both (Sets.fileRecorded 12528) (Sets.fileRecorded 12529)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M328

#print axioms Cert.M328.verified
