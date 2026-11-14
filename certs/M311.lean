import ChainOfProof
open ChainOfProof

namespace Cert.M311

def cited : List Fact := [
  ⟨11810, .fileSeen, 1427039642655743, 1, 15892, 15339⟩,
  ⟨11811, .fileSeen, 1427039642655743, 1, 15911, 15339⟩,
  ⟨11812, .fileSeen, 1427039642655743, 1, 15894, 15339⟩,
  ⟨11813, .fileSeen, 1427039642655743, 1, 15912, 15339⟩,
  ⟨11814, .fileSeen, 1427039642655743, 1, 15898, 15339⟩,
  ⟨11815, .fileSeen, 1427039642655743, 1, 15913, 15339⟩,
  ⟨11816, .fileSeen, 1427039642655743, 1, 15899, 15339⟩,
  ⟨11817, .fileSeen, 1427039642655743, 1, 15914, 15339⟩,
  ⟨11818, .fileSeen, 1427039642671343, 1, 15897, 15339⟩,
  ⟨11819, .fileSeen, 1427039642671343, 1, 15916, 15339⟩,
  ⟨11820, .fileSeen, 1427039642671343, 1, 15918, 15339⟩,
  ⟨11821, .fileSeen, 1427039642671343, 1, 15919, 15339⟩,
  ⟨11822, .fileSeen, 1427039642686943, 1, 15893, 15339⟩,
  ⟨11823, .fileSeen, 1427039642686943, 1, 15917, 15339⟩,
  ⟨11824, .fileSeen, 1427039642686943, 1, 15896, 15339⟩,
  ⟨11825, .fileSeen, 1427039642702543, 1, 15915, 15339⟩,
  ⟨11826, .fileSeen, 1427039642718143, 1, 15923, 15339⟩,
  ⟨11827, .fileSeen, 1427039642718143, 1, 15924, 15339⟩,
  ⟨11828, .fileSeen, 1427039642718143, 1, 15900, 15339⟩,
  ⟨11829, .fileSeen, 1427039642718143, 1, 15921, 15339⟩,
  ⟨11830, .fileSeen, 1427039642733743, 1, 15895, 15339⟩,
  ⟨11831, .fileSeen, 1427039642733743, 1, 15926, 15339⟩,
  ⟨11832, .fileSeen, 1427039642733743, 1, 15920, 15339⟩,
  ⟨11833, .fileSeen, 1427039643217344, 1, 15908, 15339⟩,
  ⟨11834, .fileSeen, 1427039643217344, 1, 15892, 15339⟩,
  ⟨11835, .fileSeen, 1427039643217344, 1, 15918, 15339⟩,
  ⟨11836, .fileSeen, 1427039643232944, 1, 15893, 15339⟩,
  ⟨11837, .fileSeen, 1427039643232944, 1, 15896, 15339⟩,
  ⟨11838, .fileSeen, 1427039643248544, 1, 15894, 15339⟩,
  ⟨11839, .fileSeen, 1427039643248544, 1, 15927, 15339⟩,
  ⟨11840, .fileSeen, 1427039643248544, 1, 15895, 15339⟩,
  ⟨11841, .fileSeen, 1427039643248544, 1, 15897, 15339⟩,
  ⟨11842, .fileSeen, 1427039643248544, 1, 15898, 15339⟩,
  ⟨11843, .fileSeen, 1427039643264144, 1, 15923, 15339⟩,
  ⟨11844, .fileSeen, 1427039643264144, 1, 15899, 15339⟩,
  ⟨11845, .fileSeen, 1427039643264144, 1, 15900, 15339⟩,
  ⟨11846, .fileSeen, 1427039643295344, 1, 15910, 15339⟩,
  ⟨11847, .fileSeen, 1427039643295344, 1, 15926, 15339⟩,
  ⟨11848, .fileSeen, 1427039643310944, 1, 15924, 15339⟩,
  ⟨11849, .fileSeen, 1427039643326544, 1, 15911, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11810) (.both (Sets.fileRecorded 11811) (.both (Sets.fileRecorded 11812) (.both (Sets.fileRecorded 11813) (.both (Sets.fileRecorded 11814) (.both (Sets.fileRecorded 11815) (.both (Sets.fileRecorded 11816) (.both (Sets.fileRecorded 11817) (.both (Sets.fileRecorded 11818) (.both (Sets.fileRecorded 11819) (.both (Sets.fileRecorded 11820) (.both (Sets.fileRecorded 11821) (.both (Sets.fileRecorded 11822) (.both (Sets.fileRecorded 11823) (.both (Sets.fileRecorded 11824) (.both (Sets.fileRecorded 11825) (.both (Sets.fileRecorded 11826) (.both (Sets.fileRecorded 11827) (.both (Sets.fileRecorded 11828) (.both (Sets.fileRecorded 11829) (.both (Sets.fileRecorded 11830) (.both (Sets.fileRecorded 11831) (.both (Sets.fileRecorded 11832) (.both (Sets.fileRecorded 11833) (.both (Sets.fileRecorded 11834) (.both (Sets.fileRecorded 11835) (.both (Sets.fileRecorded 11836) (.both (Sets.fileRecorded 11837) (.both (Sets.fileRecorded 11838) (.both (Sets.fileRecorded 11839) (.both (Sets.fileRecorded 11840) (.both (Sets.fileRecorded 11841) (.both (Sets.fileRecorded 11842) (.both (Sets.fileRecorded 11843) (.both (Sets.fileRecorded 11844) (.both (Sets.fileRecorded 11845) (.both (Sets.fileRecorded 11846) (.both (Sets.fileRecorded 11847) (.both (Sets.fileRecorded 11848) (Sets.fileRecorded 11849)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M311

#print axioms Cert.M311.verified
