import ChainOfProof
open ChainOfProof

namespace Cert.M288

def cited : List Fact := [
  ⟨10890, .fileSeen, 1247547263718919, 1, 15369, 15339⟩,
  ⟨10891, .fileSeen, 1247547263718919, 1, 15394, 15339⟩,
  ⟨10892, .fileSeen, 1247547263734519, 1, 15361, 15339⟩,
  ⟨10893, .fileSeen, 1247547263734519, 1, 15395, 15339⟩,
  ⟨10894, .fileSeen, 1247547263750119, 1, 15367, 15339⟩,
  ⟨10895, .fileSeen, 1247547263750119, 1, 15396, 15339⟩,
  ⟨10896, .fileSeen, 1247547263765719, 1, 15397, 15339⟩,
  ⟨10897, .fileSeen, 1247547263781320, 1, 15398, 15339⟩,
  ⟨10898, .fileSeen, 1247547264093320, 1, 15399, 15339⟩,
  ⟨10899, .fileSeen, 1247547264124520, 1, 15400, 15339⟩,
  ⟨10900, .fileSeen, 1247547264124520, 1, 15401, 15339⟩,
  ⟨10901, .fileSeen, 1247547264280520, 1, 15390, 15339⟩,
  ⟨10902, .fileSeen, 1247547264296120, 1, 15371, 15339⟩,
  ⟨10903, .fileSeen, 1247547264296120, 1, 15392, 15339⟩,
  ⟨10904, .fileSeen, 1247547264311720, 1, 15361, 15339⟩,
  ⟨10905, .fileSeen, 1247547264311720, 1, 15395, 15339⟩,
  ⟨10906, .fileSeen, 1247547264311720, 1, 15369, 15339⟩,
  ⟨10907, .fileSeen, 1247547264311720, 1, 15394, 15339⟩,
  ⟨10908, .fileSeen, 1247547264311720, 1, 15370, 15339⟩,
  ⟨10909, .fileSeen, 1247547264311720, 1, 15391, 15339⟩,
  ⟨10910, .fileSeen, 1247547264327320, 1, 15367, 15339⟩,
  ⟨10911, .fileSeen, 1247547264327320, 1, 15396, 15339⟩,
  ⟨10912, .fileSeen, 1247547264327320, 1, 15402, 15339⟩,
  ⟨10913, .fileSeen, 1247547264327320, 1, 15403, 15339⟩,
  ⟨10914, .fileSeen, 1247547264327320, 1, 15404, 15339⟩,
  ⟨10915, .fileSeen, 1247547264327320, 1, 15405, 15339⟩,
  ⟨10916, .fileSeen, 1247547264342920, 1, 15398, 15339⟩,
  ⟨10917, .fileSeen, 1247547264420921, 1, 15397, 15339⟩,
  ⟨10918, .fileSeen, 1247547264467721, 1, 15368, 15339⟩,
  ⟨10919, .fileSeen, 1247547264467721, 1, 15397, 15339⟩,
  ⟨10920, .fileSeen, 1247547264483321, 1, 15399, 15339⟩,
  ⟨10921, .fileSeen, 1247547264483321, 1, 15406, 15339⟩,
  ⟨10922, .fileSeen, 1247547264483321, 1, 15407, 15339⟩,
  ⟨10923, .fileSeen, 1247547264483321, 1, 15400, 15339⟩,
  ⟨10924, .fileSeen, 1247547264483321, 1, 15401, 15339⟩,
  ⟨10925, .fileSeen, 1247547265887323, 1, 15408, 15339⟩,
  ⟨10926, .fileSeen, 1247547265934123, 1, 15408, 15339⟩,
  ⟨10927, .fileSeen, 1247547269366129, 1, 15409, 15339⟩,
  ⟨10928, .fileSeen, 1247547269444129, 1, 15410, 15339⟩,
  ⟨10929, .fileSeen, 1247547269475330, 1, 15411, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 10890) (.both (Sets.fileRecorded 10891) (.both (Sets.fileRecorded 10892) (.both (Sets.fileRecorded 10893) (.both (Sets.fileRecorded 10894) (.both (Sets.fileRecorded 10895) (.both (Sets.fileRecorded 10896) (.both (Sets.fileRecorded 10897) (.both (Sets.fileRecorded 10898) (.both (Sets.fileRecorded 10899) (.both (Sets.fileRecorded 10900) (.both (Sets.fileRecorded 10901) (.both (Sets.fileRecorded 10902) (.both (Sets.fileRecorded 10903) (.both (Sets.fileRecorded 10904) (.both (Sets.fileRecorded 10905) (.both (Sets.fileRecorded 10906) (.both (Sets.fileRecorded 10907) (.both (Sets.fileRecorded 10908) (.both (Sets.fileRecorded 10909) (.both (Sets.fileRecorded 10910) (.both (Sets.fileRecorded 10911) (.both (Sets.fileRecorded 10912) (.both (Sets.fileRecorded 10913) (.both (Sets.fileRecorded 10914) (.both (Sets.fileRecorded 10915) (.both (Sets.fileRecorded 10916) (.both (Sets.fileRecorded 10917) (.both (Sets.fileRecorded 10918) (.both (Sets.fileRecorded 10919) (.both (Sets.fileRecorded 10920) (.both (Sets.fileRecorded 10921) (.both (Sets.fileRecorded 10922) (.both (Sets.fileRecorded 10923) (.both (Sets.fileRecorded 10924) (.both (Sets.fileRecorded 10925) (.both (Sets.fileRecorded 10926) (.both (Sets.fileRecorded 10927) (.both (Sets.fileRecorded 10928) (Sets.fileRecorded 10929)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M288

#print axioms Cert.M288.verified
