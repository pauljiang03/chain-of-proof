import ChainOfProof
open ChainOfProof

namespace Cert.M323

def cited : List Fact := [
  ⟨12290, .fileSeen, 1427144168717174, 1, 1324, 15339⟩,
  ⟨12291, .fileSeen, 1427144168717174, 1, 1326, 15339⟩,
  ⟨12292, .fileSeen, 1427144192858277, 1, 1333, 15339⟩,
  ⟨12293, .fileSeen, 1427144194219289, 1, 1333, 15339⟩,
  ⟨12294, .fileSeen, 1427203501465454, 1, 16003, 15339⟩,
  ⟨12295, .fileSeen, 1427203557000000, 1, 16055, 15339⟩,
  ⟨12296, .fileSeen, 1427203559137876, 1, 16055, 15339⟩,
  ⟨12297, .fileSeen, 1427203706325014, 1, 16056, 15339⟩,
  ⟨12298, .fileSeen, 1427203707027015, 1, 16056, 15339⟩,
  ⟨12299, .fileSeen, 1427203707042615, 1, 16057, 15339⟩,
  ⟨12300, .fileSeen, 1427203760285509, 1, 16057, 15339⟩,
  ⟨12301, .fileSeen, 1427203760285509, 1, 16057, 15339⟩,
  ⟨12302, .fileSeen, 1427203760332309, 1, 16018, 15339⟩,
  ⟨12303, .fileSeen, 1427203761049910, 1, 16016, 15339⟩,
  ⟨12304, .fileSeen, 1427203761127910, 1, 16053, 15339⟩,
  ⟨12305, .fileSeen, 1427203761143510, 1, 16019, 15339⟩,
  ⟨12306, .fileSeen, 1427203761205910, 1, 15479, 15339⟩,
  ⟨12307, .fileSeen, 1427203761221510, 1, 16015, 15339⟩,
  ⟨12308, .fileSeen, 1427203800000000, 1, 16058, 15339⟩,
  ⟨12309, .fileSeen, 1427203810891000, 1, 16055, 15339⟩,
  ⟨12310, .fileSeen, 1427203810891000, 1, 16058, 15339⟩,
  ⟨12311, .fileSeen, 1427203811749999, 1, 16055, 15339⟩,
  ⟨12312, .fileSeen, 1427203814636000, 1, 16058, 15339⟩,
  ⟨12313, .fileSeen, 1427203815197605, 1, 16058, 15339⟩,
  ⟨12314, .fileSeen, 1427204025000000, 1, 16059, 15339⟩,
  ⟨12315, .fileSeen, 1427204026614504, 1, 16059, 15339⟩,
  ⟨12316, .fileSeen, 1427204100000000, 1, 16058, 15339⟩,
  ⟨12317, .fileSeen, 1427204110350000, 1, 16059, 15339⟩,
  ⟨12318, .fileSeen, 1427204110365000, 1, 16058, 15339⟩,
  ⟨12319, .fileSeen, 1427204112222127, 1, 16059, 15339⟩,
  ⟨12320, .fileSeen, 1427204112518000, 1, 16058, 15339⟩,
  ⟨12321, .fileSeen, 1427204113454529, 1, 16058, 15339⟩,
  ⟨12322, .fileSeen, 1427204409308053, 1, 12629, 15339⟩,
  ⟨12323, .fileSeen, 1427204409417254, 1, 12631, 15339⟩,
  ⟨12324, .fileSeen, 1427204410337655, 1, 12630, 15339⟩,
  ⟨12325, .fileSeen, 1427204411133257, 1, 12633, 15339⟩,
  ⟨12326, .fileSeen, 1427204413161260, 1, 12628, 15339⟩,
  ⟨12327, .fileSeen, 1427204877822079, 1, 15480, 15339⟩,
  ⟨12328, .fileSeen, 1427204877993680, 1, 15482, 15339⟩,
  ⟨12329, .fileSeen, 1427204878118480, 1, 15477, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12290) (.both (Sets.fileRecorded 12291) (.both (Sets.fileRecorded 12292) (.both (Sets.fileRecorded 12293) (.both (Sets.fileRecorded 12294) (.both (Sets.fileRecorded 12295) (.both (Sets.fileRecorded 12296) (.both (Sets.fileRecorded 12297) (.both (Sets.fileRecorded 12298) (.both (Sets.fileRecorded 12299) (.both (Sets.fileRecorded 12300) (.both (Sets.fileRecorded 12301) (.both (Sets.fileRecorded 12302) (.both (Sets.fileRecorded 12303) (.both (Sets.fileRecorded 12304) (.both (Sets.fileRecorded 12305) (.both (Sets.fileRecorded 12306) (.both (Sets.fileRecorded 12307) (.both (Sets.fileRecorded 12308) (.both (Sets.fileRecorded 12309) (.both (Sets.fileRecorded 12310) (.both (Sets.fileRecorded 12311) (.both (Sets.fileRecorded 12312) (.both (Sets.fileRecorded 12313) (.both (Sets.fileRecorded 12314) (.both (Sets.fileRecorded 12315) (.both (Sets.fileRecorded 12316) (.both (Sets.fileRecorded 12317) (.both (Sets.fileRecorded 12318) (.both (Sets.fileRecorded 12319) (.both (Sets.fileRecorded 12320) (.both (Sets.fileRecorded 12321) (.both (Sets.fileRecorded 12322) (.both (Sets.fileRecorded 12323) (.both (Sets.fileRecorded 12324) (.both (Sets.fileRecorded 12325) (.both (Sets.fileRecorded 12326) (.both (Sets.fileRecorded 12327) (.both (Sets.fileRecorded 12328) (Sets.fileRecorded 12329)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M323

#print axioms Cert.M323.verified
