import ChainOfProof
open ChainOfProof

namespace Cert.M313

def cited : List Fact := [
  ⟨11890, .fileSeen, 1427039645109349, 1, 15950, 15339⟩,
  ⟨11891, .fileSeen, 1427039645109349, 1, 15473, 15339⟩,
  ⟨11892, .fileSeen, 1427039645109349, 1, 15474, 15339⟩,
  ⟨11893, .fileSeen, 1427039645109349, 1, 15951, 15339⟩,
  ⟨11894, .fileSeen, 1427039645119349, 1, 15950, 15339⟩,
  ⟨11895, .fileSeen, 1427039645119349, 1, 15951, 15339⟩,
  ⟨11896, .fileSeen, 1427039647171753, 1, 15950, 15339⟩,
  ⟨11897, .fileSeen, 1427039647187353, 1, 15473, 15339⟩,
  ⟨11898, .fileSeen, 1427039647218553, 1, 15474, 15339⟩,
  ⟨11899, .fileSeen, 1427039647218553, 1, 15951, 15339⟩,
  ⟨11900, .fileSeen, 1427039655361767, 1, 15352, 15339⟩,
  ⟨11901, .fileSeen, 1427039655361767, 1, 15353, 15339⟩,
  ⟨11902, .fileSeen, 1427039655361767, 1, 15467, 15339⟩,
  ⟨11903, .fileSeen, 1427039655377367, 1, 15351, 15339⟩,
  ⟨11904, .fileSeen, 1427039655377367, 1, 15441, 15339⟩,
  ⟨11905, .fileSeen, 1427039655377367, 1, 15378, 15339⟩,
  ⟨11906, .fileSeen, 1427039655377367, 1, 15461, 15339⟩,
  ⟨11907, .fileSeen, 1427039655377367, 1, 15354, 15339⟩,
  ⟨11908, .fileSeen, 1427039655392967, 1, 15395, 15339⟩,
  ⟨11909, .fileSeen, 1427039655392967, 1, 15393, 15339⟩,
  ⟨11910, .fileSeen, 1427039655392967, 1, 15376, 15339⟩,
  ⟨11911, .fileSeen, 1427039752376253, 1, 15902, 15339⟩,
  ⟨11912, .fileSeen, 1427039752376253, 1, 15905, 15339⟩,
  ⟨11913, .fileSeen, 1427039752376253, 1, 15906, 15339⟩,
  ⟨11914, .fileSeen, 1427039752516653, 1, 15902, 15339⟩,
  ⟨11915, .fileSeen, 1427039752532253, 1, 15904, 15339⟩,
  ⟨11916, .fileSeen, 1427039752563453, 1, 15905, 15339⟩,
  ⟨11917, .fileSeen, 1427039752563453, 1, 15906, 15339⟩,
  ⟨11918, .fileSeen, 1427039757290262, 1, 1457, 15339⟩,
  ⟨11919, .fileSeen, 1427039757290262, 1, 15952, 15339⟩,
  ⟨11920, .fileSeen, 1427039757290262, 1, 15953, 15339⟩,
  ⟨11921, .fileSeen, 1427039757290262, 1, 1458, 15339⟩,
  ⟨11922, .fileSeen, 1427039757290262, 1, 15954, 15339⟩,
  ⟨11923, .fileSeen, 1427039757290262, 1, 15955, 15339⟩,
  ⟨11924, .fileSeen, 1427039757290262, 1, 15956, 15339⟩,
  ⟨11925, .fileSeen, 1427039757290262, 1, 15957, 15339⟩,
  ⟨11926, .fileSeen, 1427039757290262, 1, 15958, 15339⟩,
  ⟨11927, .fileSeen, 1427039757290262, 1, 15959, 15339⟩,
  ⟨11928, .fileSeen, 1427039757290262, 1, 15960, 15453⟩,
  ⟨11929, .fileSeen, 1427039757290262, 1, 15960, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11890) (.both (Sets.fileRecorded 11891) (.both (Sets.fileRecorded 11892) (.both (Sets.fileRecorded 11893) (.both (Sets.fileRecorded 11894) (.both (Sets.fileRecorded 11895) (.both (Sets.fileRecorded 11896) (.both (Sets.fileRecorded 11897) (.both (Sets.fileRecorded 11898) (.both (Sets.fileRecorded 11899) (.both (Sets.fileRecorded 11900) (.both (Sets.fileRecorded 11901) (.both (Sets.fileRecorded 11902) (.both (Sets.fileRecorded 11903) (.both (Sets.fileRecorded 11904) (.both (Sets.fileRecorded 11905) (.both (Sets.fileRecorded 11906) (.both (Sets.fileRecorded 11907) (.both (Sets.fileRecorded 11908) (.both (Sets.fileRecorded 11909) (.both (Sets.fileRecorded 11910) (.both (Sets.fileRecorded 11911) (.both (Sets.fileRecorded 11912) (.both (Sets.fileRecorded 11913) (.both (Sets.fileRecorded 11914) (.both (Sets.fileRecorded 11915) (.both (Sets.fileRecorded 11916) (.both (Sets.fileRecorded 11917) (.both (Sets.fileRecorded 11918) (.both (Sets.fileRecorded 11919) (.both (Sets.fileRecorded 11920) (.both (Sets.fileRecorded 11921) (.both (Sets.fileRecorded 11922) (.both (Sets.fileRecorded 11923) (.both (Sets.fileRecorded 11924) (.both (Sets.fileRecorded 11925) (.both (Sets.fileRecorded 11926) (.both (Sets.fileRecorded 11927) (.both (Sets.fileRecorded 11928) (Sets.fileRecorded 11929)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M313

#print axioms Cert.M313.verified
