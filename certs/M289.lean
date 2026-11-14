import ChainOfProof
open ChainOfProof

namespace Cert.M289

def cited : List Fact := [
  ⟨10930, .fileSeen, 1247547272704535, 1, 15412, 15339⟩,
  ⟨10931, .fileSeen, 1247547272844935, 1, 15412, 15339⟩,
  ⟨10932, .fileSeen, 1247547297882979, 1, 15413, 15339⟩,
  ⟨10933, .fileSeen, 1247547297898579, 1, 15413, 15339⟩,
  ⟨10934, .fileSeen, 1247547297976580, 1, 15414, 15339⟩,
  ⟨10935, .fileSeen, 1247547298007780, 1, 15414, 15339⟩,
  ⟨10936, .fileSeen, 1247547298881381, 1, 15415, 15339⟩,
  ⟨10937, .fileSeen, 1247547298928181, 1, 15415, 15339⟩,
  ⟨10938, .fileSeen, 1247547298959381, 1, 15416, 15339⟩,
  ⟨10939, .fileSeen, 1247547298990581, 1, 15416, 15339⟩,
  ⟨10940, .fileSeen, 1247547299442982, 1, 15417, 15339⟩,
  ⟨10941, .fileSeen, 1247547299458582, 1, 15417, 15339⟩,
  ⟨10942, .fileSeen, 1247547299801783, 1, 15418, 15339⟩,
  ⟨10943, .fileSeen, 1247547299848583, 1, 15418, 15339⟩,
  ⟨10944, .fileSeen, 1247547300722184, 1, 15419, 15339⟩,
  ⟨10945, .fileSeen, 1247547300753384, 1, 15419, 15339⟩,
  ⟨10946, .fileSeen, 1247547300815785, 1, 15420, 15339⟩,
  ⟨10947, .fileSeen, 1247547300846985, 1, 15420, 15339⟩,
  ⟨10948, .fileSeen, 1247547300940585, 1, 15421, 15339⟩,
  ⟨10949, .fileSeen, 1247547301018585, 1, 15422, 15339⟩,
  ⟨10950, .fileSeen, 1247547301034185, 1, 15422, 15339⟩,
  ⟨10951, .fileSeen, 1247547426598805, 1, 15423, 15339⟩,
  ⟨10952, .fileSeen, 1247547427066806, 1, 15424, 15339⟩,
  ⟨10953, .fileSeen, 1247547427238407, 1, 15425, 15339⟩,
  ⟨10954, .fileSeen, 1247547427378807, 1, 15358, 15339⟩,
  ⟨10955, .fileSeen, 1247547427378807, 1, 15426, 15339⟩,
  ⟨10956, .fileSeen, 1247547427394407, 1, 15358, 15339⟩,
  ⟨10957, .fileSeen, 1247547427394407, 1, 15352, 15339⟩,
  ⟨10958, .fileSeen, 1247547427924808, 1, 15427, 15339⟩,
  ⟨10959, .fileSeen, 1247547428049608, 1, 15428, 15339⟩,
  ⟨10960, .fileSeen, 1247547428907610, 1, 15429, 15339⟩,
  ⟨10961, .fileSeen, 1247547428954410, 1, 15430, 15339⟩,
  ⟨10962, .fileSeen, 1247547429001210, 1, 15360, 15339⟩,
  ⟨10963, .fileSeen, 1247547429001210, 1, 15431, 15339⟩,
  ⟨10964, .fileSeen, 1247547429016810, 1, 15360, 15339⟩,
  ⟨10965, .fileSeen, 1247547429016810, 1, 15354, 15339⟩,
  ⟨10966, .fileSeen, 1247547429141610, 1, 15432, 15339⟩,
  ⟨10967, .fileSeen, 1247547429172810, 1, 15359, 15339⟩,
  ⟨10968, .fileSeen, 1247547429172810, 1, 15353, 15339⟩,
  ⟨10969, .fileSeen, 1247547429172810, 1, 15433, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 10930) (.both (Sets.fileRecorded 10931) (.both (Sets.fileRecorded 10932) (.both (Sets.fileRecorded 10933) (.both (Sets.fileRecorded 10934) (.both (Sets.fileRecorded 10935) (.both (Sets.fileRecorded 10936) (.both (Sets.fileRecorded 10937) (.both (Sets.fileRecorded 10938) (.both (Sets.fileRecorded 10939) (.both (Sets.fileRecorded 10940) (.both (Sets.fileRecorded 10941) (.both (Sets.fileRecorded 10942) (.both (Sets.fileRecorded 10943) (.both (Sets.fileRecorded 10944) (.both (Sets.fileRecorded 10945) (.both (Sets.fileRecorded 10946) (.both (Sets.fileRecorded 10947) (.both (Sets.fileRecorded 10948) (.both (Sets.fileRecorded 10949) (.both (Sets.fileRecorded 10950) (.both (Sets.fileRecorded 10951) (.both (Sets.fileRecorded 10952) (.both (Sets.fileRecorded 10953) (.both (Sets.fileRecorded 10954) (.both (Sets.fileRecorded 10955) (.both (Sets.fileRecorded 10956) (.both (Sets.fileRecorded 10957) (.both (Sets.fileRecorded 10958) (.both (Sets.fileRecorded 10959) (.both (Sets.fileRecorded 10960) (.both (Sets.fileRecorded 10961) (.both (Sets.fileRecorded 10962) (.both (Sets.fileRecorded 10963) (.both (Sets.fileRecorded 10964) (.both (Sets.fileRecorded 10965) (.both (Sets.fileRecorded 10966) (.both (Sets.fileRecorded 10967) (.both (Sets.fileRecorded 10968) (Sets.fileRecorded 10969)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M289

#print axioms Cert.M289.verified
