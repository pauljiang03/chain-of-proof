import ChainOfProof
open ChainOfProof

namespace Cert.M325

def cited : List Fact := [
  ⟨12370, .fileSeen, 1427210194272291, 1, 15850, 15339⟩,
  ⟨12371, .fileSeen, 1427210194303491, 1, 15851, 15339⟩,
  ⟨12372, .fileSeen, 1427210194319091, 1, 15858, 15339⟩,
  ⟨12373, .fileSeen, 1427210194350291, 1, 15849, 15339⟩,
  ⟨12374, .fileSeen, 1427210194381491, 1, 15854, 15339⟩,
  ⟨12375, .fileSeen, 1427210194412692, 1, 15426, 15339⟩,
  ⟨12376, .fileSeen, 1427210194428292, 1, 15432, 15339⟩,
  ⟨12377, .fileSeen, 1427210194475092, 1, 15433, 15339⟩,
  ⟨12378, .fileSeen, 1427210194506292, 1, 15411, 15339⟩,
  ⟨12379, .fileSeen, 1427210194521892, 1, 15413, 15339⟩,
  ⟨12380, .fileSeen, 1427210194537492, 1, 15380, 15339⟩,
  ⟨12381, .fileSeen, 1427210194553092, 1, 15382, 15339⟩,
  ⟨12382, .fileSeen, 1427210194568692, 1, 15416, 15339⟩,
  ⟨12383, .fileSeen, 1427210194599892, 1, 15408, 15339⟩,
  ⟨12384, .fileSeen, 1427210194615492, 1, 15420, 15339⟩,
  ⟨12385, .fileSeen, 1427210194631092, 1, 16062, 15339⟩,
  ⟨12386, .fileSeen, 1427210194646692, 1, 16063, 15339⟩,
  ⟨12387, .fileSeen, 1427210194693492, 1, 16064, 15339⟩,
  ⟨12388, .fileSeen, 1427210194709092, 1, 15440, 15339⟩,
  ⟨12389, .fileSeen, 1427210194709092, 1, 15460, 15339⟩,
  ⟨12390, .fileSeen, 1427210194724692, 1, 15443, 15339⟩,
  ⟨12391, .fileSeen, 1427210194740292, 1, 15459, 15339⟩,
  ⟨12392, .fileSeen, 1427210194755892, 1, 15415, 15339⟩,
  ⟨12393, .fileSeen, 1427210194771492, 1, 15434, 15339⟩,
  ⟨12394, .fileSeen, 1427210194802692, 1, 15414, 15339⟩,
  ⟨12395, .fileSeen, 1427210194818292, 1, 15430, 15339⟩,
  ⟨12396, .fileSeen, 1427210194818292, 1, 16065, 15339⟩,
  ⟨12397, .fileSeen, 1427210194833892, 1, 16066, 15339⟩,
  ⟨12398, .fileSeen, 1427210194849492, 1, 15412, 15339⟩,
  ⟨12399, .fileSeen, 1427210194849492, 1, 15384, 15339⟩,
  ⟨12400, .fileSeen, 1427210194865092, 1, 16067, 15339⟩,
  ⟨12401, .fileSeen, 1427210194880692, 1, 16068, 15339⟩,
  ⟨12402, .fileSeen, 1427210194880692, 1, 16069, 15339⟩,
  ⟨12403, .fileSeen, 1427210194896292, 1, 15419, 15339⟩,
  ⟨12404, .fileSeen, 1427210194896292, 1, 15389, 15339⟩,
  ⟨12405, .fileSeen, 1427210194911892, 1, 15458, 15339⟩,
  ⟨12406, .fileSeen, 1427210194927492, 1, 15410, 15339⟩,
  ⟨12407, .fileSeen, 1427210194927492, 1, 15385, 15339⟩,
  ⟨12408, .fileSeen, 1427210194989893, 1, 15379, 15339⟩,
  ⟨12409, .fileSeen, 1427210195005493, 1, 15386, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12370) (.both (Sets.fileRecorded 12371) (.both (Sets.fileRecorded 12372) (.both (Sets.fileRecorded 12373) (.both (Sets.fileRecorded 12374) (.both (Sets.fileRecorded 12375) (.both (Sets.fileRecorded 12376) (.both (Sets.fileRecorded 12377) (.both (Sets.fileRecorded 12378) (.both (Sets.fileRecorded 12379) (.both (Sets.fileRecorded 12380) (.both (Sets.fileRecorded 12381) (.both (Sets.fileRecorded 12382) (.both (Sets.fileRecorded 12383) (.both (Sets.fileRecorded 12384) (.both (Sets.fileRecorded 12385) (.both (Sets.fileRecorded 12386) (.both (Sets.fileRecorded 12387) (.both (Sets.fileRecorded 12388) (.both (Sets.fileRecorded 12389) (.both (Sets.fileRecorded 12390) (.both (Sets.fileRecorded 12391) (.both (Sets.fileRecorded 12392) (.both (Sets.fileRecorded 12393) (.both (Sets.fileRecorded 12394) (.both (Sets.fileRecorded 12395) (.both (Sets.fileRecorded 12396) (.both (Sets.fileRecorded 12397) (.both (Sets.fileRecorded 12398) (.both (Sets.fileRecorded 12399) (.both (Sets.fileRecorded 12400) (.both (Sets.fileRecorded 12401) (.both (Sets.fileRecorded 12402) (.both (Sets.fileRecorded 12403) (.both (Sets.fileRecorded 12404) (.both (Sets.fileRecorded 12405) (.both (Sets.fileRecorded 12406) (.both (Sets.fileRecorded 12407) (.both (Sets.fileRecorded 12408) (Sets.fileRecorded 12409)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M325

#print axioms Cert.M325.verified
