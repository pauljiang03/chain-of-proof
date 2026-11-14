import ChainOfProof
open ChainOfProof

namespace Cert.M287

def cited : List Fact := [
  ⟨10850, .fileSeen, 1247541608961010, 1, 15369, 15339⟩,
  ⟨10851, .fileSeen, 1247541608961010, 1, 15370, 15339⟩,
  ⟨10852, .fileSeen, 1247541608961010, 1, 15371, 15339⟩,
  ⟨10853, .fileSeen, 1247546754757660, 1, 15372, 15339⟩,
  ⟨10854, .fileSeen, 1247546754804460, 1, 15373, 15339⟩,
  ⟨10855, .fileSeen, 1247546754835660, 1, 15374, 15339⟩,
  ⟨10856, .fileSeen, 1247546754898060, 1, 15373, 15339⟩,
  ⟨10857, .fileSeen, 1247546754913660, 1, 15372, 15339⟩,
  ⟨10858, .fileSeen, 1247546754913660, 1, 15374, 15339⟩,
  ⟨10859, .fileSeen, 1247546980443256, 1, 15375, 15339⟩,
  ⟨10860, .fileSeen, 1247546980458856, 1, 15376, 15339⟩,
  ⟨10861, .fileSeen, 1247547213440031, 1, 15377, 15339⟩,
  ⟨10862, .fileSeen, 1247547213455631, 1, 15377, 15339⟩,
  ⟨10863, .fileSeen, 1247547213455631, 1, 15378, 15339⟩,
  ⟨10864, .fileSeen, 1247547213642831, 1, 15379, 15339⟩,
  ⟨10865, .fileSeen, 1247547213689632, 1, 15380, 15339⟩,
  ⟨10866, .fileSeen, 1247547229976060, 1, 15381, 15339⟩,
  ⟨10867, .fileSeen, 1247547230022860, 1, 15382, 15339⟩,
  ⟨10868, .fileSeen, 1247547230178860, 1, 15381, 15339⟩,
  ⟨10869, .fileSeen, 1247547230210061, 1, 15382, 15339⟩,
  ⟨10870, .fileSeen, 1247547231972864, 1, 15383, 15339⟩,
  ⟨10871, .fileSeen, 1247547232019664, 1, 15383, 15339⟩,
  ⟨10872, .fileSeen, 1247547235264469, 1, 15384, 15339⟩,
  ⟨10873, .fileSeen, 1247547235326870, 1, 15384, 15339⟩,
  ⟨10874, .fileSeen, 1247547238400075, 1, 15385, 15339⟩,
  ⟨10875, .fileSeen, 1247547238602875, 1, 15385, 15339⟩,
  ⟨10876, .fileSeen, 1247547245700888, 1, 15386, 15339⟩,
  ⟨10877, .fileSeen, 1247547245732088, 1, 15386, 15339⟩,
  ⟨10878, .fileSeen, 1247547261581716, 1, 15387, 15339⟩,
  ⟨10879, .fileSeen, 1247547261628516, 1, 15387, 15339⟩,
  ⟨10880, .fileSeen, 1247547261971716, 1, 15388, 15339⟩,
  ⟨10881, .fileSeen, 1247547262002916, 1, 15388, 15339⟩,
  ⟨10882, .fileSeen, 1247547263375719, 1, 15389, 15339⟩,
  ⟨10883, .fileSeen, 1247547263422519, 1, 15389, 15339⟩,
  ⟨10884, .fileSeen, 1247547263656519, 1, 15390, 15339⟩,
  ⟨10885, .fileSeen, 1247547263703319, 1, 15370, 15339⟩,
  ⟨10886, .fileSeen, 1247547263703319, 1, 15391, 15339⟩,
  ⟨10887, .fileSeen, 1247547263703319, 1, 15371, 15339⟩,
  ⟨10888, .fileSeen, 1247547263703319, 1, 15392, 15339⟩,
  ⟨10889, .fileSeen, 1247547263718919, 1, 15393, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 10850) (.both (Sets.fileRecorded 10851) (.both (Sets.fileRecorded 10852) (.both (Sets.fileRecorded 10853) (.both (Sets.fileRecorded 10854) (.both (Sets.fileRecorded 10855) (.both (Sets.fileRecorded 10856) (.both (Sets.fileRecorded 10857) (.both (Sets.fileRecorded 10858) (.both (Sets.fileRecorded 10859) (.both (Sets.fileRecorded 10860) (.both (Sets.fileRecorded 10861) (.both (Sets.fileRecorded 10862) (.both (Sets.fileRecorded 10863) (.both (Sets.fileRecorded 10864) (.both (Sets.fileRecorded 10865) (.both (Sets.fileRecorded 10866) (.both (Sets.fileRecorded 10867) (.both (Sets.fileRecorded 10868) (.both (Sets.fileRecorded 10869) (.both (Sets.fileRecorded 10870) (.both (Sets.fileRecorded 10871) (.both (Sets.fileRecorded 10872) (.both (Sets.fileRecorded 10873) (.both (Sets.fileRecorded 10874) (.both (Sets.fileRecorded 10875) (.both (Sets.fileRecorded 10876) (.both (Sets.fileRecorded 10877) (.both (Sets.fileRecorded 10878) (.both (Sets.fileRecorded 10879) (.both (Sets.fileRecorded 10880) (.both (Sets.fileRecorded 10881) (.both (Sets.fileRecorded 10882) (.both (Sets.fileRecorded 10883) (.both (Sets.fileRecorded 10884) (.both (Sets.fileRecorded 10885) (.both (Sets.fileRecorded 10886) (.both (Sets.fileRecorded 10887) (.both (Sets.fileRecorded 10888) (Sets.fileRecorded 10889)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M287

#print axioms Cert.M287.verified
