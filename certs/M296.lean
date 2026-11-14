import ChainOfProof
open ChainOfProof

namespace Cert.M296

def cited : List Fact := [
  ⟨11210, .fileSeen, 1427034897376739, 1, 15530, 15339⟩,
  ⟨11211, .fileSeen, 1427034897392339, 1, 15525, 15339⟩,
  ⟨11212, .fileSeen, 1427034897392339, 1, 15531, 15339⟩,
  ⟨11213, .fileSeen, 1427034897392339, 1, 15532, 15339⟩,
  ⟨11214, .fileSeen, 1427034897392339, 1, 15533, 15339⟩,
  ⟨11215, .fileSeen, 1427034897392339, 1, 15534, 15339⟩,
  ⟨11216, .fileSeen, 1427034897407939, 1, 15534, 15339⟩,
  ⟨11217, .fileSeen, 1427034897407939, 1, 15535, 15339⟩,
  ⟨11218, .fileSeen, 1427034897407939, 1, 15536, 15339⟩,
  ⟨11219, .fileSeen, 1427034897407939, 1, 15537, 15339⟩,
  ⟨11220, .fileSeen, 1427034897407939, 1, 15538, 15339⟩,
  ⟨11221, .fileSeen, 1427034897423539, 1, 15539, 15339⟩,
  ⟨11222, .fileSeen, 1427034897423539, 1, 15540, 15339⟩,
  ⟨11223, .fileSeen, 1427034897423539, 1, 15522, 15339⟩,
  ⟨11224, .fileSeen, 1427034897423539, 1, 15541, 15339⟩,
  ⟨11225, .fileSeen, 1427034897766739, 1, 15542, 15339⟩,
  ⟨11226, .fileSeen, 1427034898453140, 1, 15370, 15339⟩,
  ⟨11227, .fileSeen, 1427034898453140, 1, 15371, 15339⟩,
  ⟨11228, .fileSeen, 1427034898468740, 1, 15366, 15339⟩,
  ⟨11229, .fileSeen, 1427034898468740, 1, 15369, 15339⟩,
  ⟨11230, .fileSeen, 1427034899825943, 1, 15492, 15339⟩,
  ⟨11231, .fileSeen, 1427034899825943, 1, 15507, 15339⟩,
  ⟨11232, .fileSeen, 1427034899825943, 1, 15486, 15339⟩,
  ⟨11233, .fileSeen, 1427034899825943, 1, 15508, 15339⟩,
  ⟨11234, .fileSeen, 1427034899825943, 1, 15487, 15339⟩,
  ⟨11235, .fileSeen, 1427034899825943, 1, 15506, 15339⟩,
  ⟨11236, .fileSeen, 1427034899841543, 1, 15503, 15339⟩,
  ⟨11237, .fileSeen, 1427034899841543, 1, 15504, 15339⟩,
  ⟨11238, .fileSeen, 1427034899841543, 1, 15509, 15339⟩,
  ⟨11239, .fileSeen, 1427034899841543, 1, 15485, 15339⟩,
  ⟨11240, .fileSeen, 1427034899841543, 1, 15511, 15339⟩,
  ⟨11241, .fileSeen, 1427034899857143, 1, 15493, 15339⟩,
  ⟨11242, .fileSeen, 1427034899857143, 1, 15512, 15339⟩,
  ⟨11243, .fileSeen, 1427034899857143, 1, 15513, 15339⟩,
  ⟨11244, .fileSeen, 1427034899857143, 1, 15514, 15339⟩,
  ⟨11245, .fileSeen, 1427034899872743, 1, 15494, 15339⟩,
  ⟨11246, .fileSeen, 1427034899872743, 1, 15510, 15339⟩,
  ⟨11247, .fileSeen, 1427034899888343, 1, 15521, 15339⟩,
  ⟨11248, .fileSeen, 1427034899888343, 1, 15488, 15339⟩,
  ⟨11249, .fileSeen, 1427034899888343, 1, 15516, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11210) (.both (Sets.fileRecorded 11211) (.both (Sets.fileRecorded 11212) (.both (Sets.fileRecorded 11213) (.both (Sets.fileRecorded 11214) (.both (Sets.fileRecorded 11215) (.both (Sets.fileRecorded 11216) (.both (Sets.fileRecorded 11217) (.both (Sets.fileRecorded 11218) (.both (Sets.fileRecorded 11219) (.both (Sets.fileRecorded 11220) (.both (Sets.fileRecorded 11221) (.both (Sets.fileRecorded 11222) (.both (Sets.fileRecorded 11223) (.both (Sets.fileRecorded 11224) (.both (Sets.fileRecorded 11225) (.both (Sets.fileRecorded 11226) (.both (Sets.fileRecorded 11227) (.both (Sets.fileRecorded 11228) (.both (Sets.fileRecorded 11229) (.both (Sets.fileRecorded 11230) (.both (Sets.fileRecorded 11231) (.both (Sets.fileRecorded 11232) (.both (Sets.fileRecorded 11233) (.both (Sets.fileRecorded 11234) (.both (Sets.fileRecorded 11235) (.both (Sets.fileRecorded 11236) (.both (Sets.fileRecorded 11237) (.both (Sets.fileRecorded 11238) (.both (Sets.fileRecorded 11239) (.both (Sets.fileRecorded 11240) (.both (Sets.fileRecorded 11241) (.both (Sets.fileRecorded 11242) (.both (Sets.fileRecorded 11243) (.both (Sets.fileRecorded 11244) (.both (Sets.fileRecorded 11245) (.both (Sets.fileRecorded 11246) (.both (Sets.fileRecorded 11247) (.both (Sets.fileRecorded 11248) (Sets.fileRecorded 11249)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M296

#print axioms Cert.M296.verified
