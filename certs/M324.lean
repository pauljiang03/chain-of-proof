import ChainOfProof
open ChainOfProof

namespace Cert.M324

def cited : List Fact := [
  ⟨12330, .fileSeen, 1427204878305680, 1, 15478, 15339⟩,
  ⟨12331, .fileSeen, 1427204878430480, 1, 15481, 15339⟩,
  ⟨12332, .fileSeen, 1427204878586481, 1, 12642, 15339⟩,
  ⟨12333, .fileSeen, 1427204907992133, 1, 15481, 15339⟩,
  ⟨12334, .fileSeen, 1427204916260147, 1, 15478, 15339⟩,
  ⟨12335, .fileSeen, 1427204986117070, 1, 15477, 15339⟩,
  ⟨12336, .fileSeen, 1427204986897071, 1, 15482, 15339⟩,
  ⟨12337, .fileSeen, 1427204987084272, 1, 15480, 15339⟩,
  ⟨12338, .fileSeen, 1427205078803644, 1, 12628, 15339⟩,
  ⟨12339, .fileSeen, 1427205079037645, 1, 12629, 15339⟩,
  ⟨12340, .fileSeen, 1427205079037645, 1, 12630, 15339⟩,
  ⟨12341, .fileSeen, 1427205079037645, 1, 12631, 15339⟩,
  ⟨12342, .fileSeen, 1427205083358852, 1, 12642, 15339⟩,
  ⟨12343, .fileSeen, 1427205084856455, 1, 12633, 15339⟩,
  ⟨12344, .fileSeen, 1427205084872055, 1, 12642, 15339⟩,
  ⟨12345, .fileSeen, 1427205915964751, 1, 16060, 15453⟩,
  ⟨12346, .fileSeen, 1427205915984751, 1, 16060, 15453⟩,
  ⟨12347, .fileSeen, 1427205915984751, 1, 16061, 15453⟩,
  ⟨12348, .fileSeen, 1427205915994751, 1, 16061, 15453⟩,
  ⟨12349, .fileSeen, 1427206585926000, 1, 15845, 15453⟩,
  ⟨12350, .fileSeen, 1427210193835491, 1, 15444, 15339⟩,
  ⟨12351, .fileSeen, 1427210193866691, 1, 16035, 15339⟩,
  ⟨12352, .fileSeen, 1427210193897891, 1, 16034, 15339⟩,
  ⟨12353, .fileSeen, 1427210193913491, 1, 16033, 15339⟩,
  ⟨12354, .fileSeen, 1427210193944691, 1, 16032, 15339⟩,
  ⟨12355, .fileSeen, 1427210193944691, 1, 16030, 15339⟩,
  ⟨12356, .fileSeen, 1427210193991491, 1, 16029, 15339⟩,
  ⟨12357, .fileSeen, 1427210194007091, 1, 16028, 15339⟩,
  ⟨12358, .fileSeen, 1427210194053891, 1, 16027, 15339⟩,
  ⟨12359, .fileSeen, 1427210194069491, 1, 16025, 15339⟩,
  ⟨12360, .fileSeen, 1427210194085091, 1, 16026, 15339⟩,
  ⟨12361, .fileSeen, 1427210194116291, 1, 16024, 15339⟩,
  ⟨12362, .fileSeen, 1427210194131891, 1, 16023, 15339⟩,
  ⟨12363, .fileSeen, 1427210194147491, 1, 16021, 15339⟩,
  ⟨12364, .fileSeen, 1427210194163091, 1, 15861, 15339⟩,
  ⟨12365, .fileSeen, 1427210194178691, 1, 15855, 15339⟩,
  ⟨12366, .fileSeen, 1427210194194291, 1, 15857, 15339⟩,
  ⟨12367, .fileSeen, 1427210194209891, 1, 15852, 15339⟩,
  ⟨12368, .fileSeen, 1427210194225491, 1, 15853, 15339⟩,
  ⟨12369, .fileSeen, 1427210194256691, 1, 15856, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12330) (.both (Sets.fileRecorded 12331) (.both (Sets.fileRecorded 12332) (.both (Sets.fileRecorded 12333) (.both (Sets.fileRecorded 12334) (.both (Sets.fileRecorded 12335) (.both (Sets.fileRecorded 12336) (.both (Sets.fileRecorded 12337) (.both (Sets.fileRecorded 12338) (.both (Sets.fileRecorded 12339) (.both (Sets.fileRecorded 12340) (.both (Sets.fileRecorded 12341) (.both (Sets.fileRecorded 12342) (.both (Sets.fileRecorded 12343) (.both (Sets.fileRecorded 12344) (.both (Sets.fileRecorded 12345) (.both (Sets.fileRecorded 12346) (.both (Sets.fileRecorded 12347) (.both (Sets.fileRecorded 12348) (.both (Sets.fileRecorded 12349) (.both (Sets.fileRecorded 12350) (.both (Sets.fileRecorded 12351) (.both (Sets.fileRecorded 12352) (.both (Sets.fileRecorded 12353) (.both (Sets.fileRecorded 12354) (.both (Sets.fileRecorded 12355) (.both (Sets.fileRecorded 12356) (.both (Sets.fileRecorded 12357) (.both (Sets.fileRecorded 12358) (.both (Sets.fileRecorded 12359) (.both (Sets.fileRecorded 12360) (.both (Sets.fileRecorded 12361) (.both (Sets.fileRecorded 12362) (.both (Sets.fileRecorded 12363) (.both (Sets.fileRecorded 12364) (.both (Sets.fileRecorded 12365) (.both (Sets.fileRecorded 12366) (.both (Sets.fileRecorded 12367) (.both (Sets.fileRecorded 12368) (Sets.fileRecorded 12369)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M324

#print axioms Cert.M324.verified
