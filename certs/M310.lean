import ChainOfProof
open ChainOfProof

namespace Cert.M310

def cited : List Fact := [
  ⟨11770, .fileSeen, 1427039628288118, 1, 15908, 15339⟩,
  ⟨11771, .fileSeen, 1427039628288118, 1, 15910, 15339⟩,
  ⟨11772, .fileSeen, 1427039628334918, 1, 15910, 15339⟩,
  ⟨11773, .fileSeen, 1427039628397318, 1, 15544, 15339⟩,
  ⟨11774, .fileSeen, 1427039629536120, 1, 15390, 15339⟩,
  ⟨11775, .fileSeen, 1427039636431332, 1, 15892, 15339⟩,
  ⟨11776, .fileSeen, 1427039636431332, 1, 15911, 15339⟩,
  ⟨11777, .fileSeen, 1427039636431332, 1, 15912, 15339⟩,
  ⟨11778, .fileSeen, 1427039636431332, 1, 15898, 15339⟩,
  ⟨11779, .fileSeen, 1427039636431332, 1, 15913, 15339⟩,
  ⟨11780, .fileSeen, 1427039636431332, 1, 15899, 15339⟩,
  ⟨11781, .fileSeen, 1427039636431332, 1, 15914, 15339⟩,
  ⟨11782, .fileSeen, 1427039636446932, 1, 15896, 15339⟩,
  ⟨11783, .fileSeen, 1427039636446932, 1, 15915, 15339⟩,
  ⟨11784, .fileSeen, 1427039636446932, 1, 15897, 15339⟩,
  ⟨11785, .fileSeen, 1427039636446932, 1, 15916, 15339⟩,
  ⟨11786, .fileSeen, 1427039636478132, 1, 15893, 15339⟩,
  ⟨11787, .fileSeen, 1427039636478132, 1, 15917, 15339⟩,
  ⟨11788, .fileSeen, 1427039636478132, 1, 15918, 15339⟩,
  ⟨11789, .fileSeen, 1427039636478132, 1, 15919, 15339⟩,
  ⟨11790, .fileSeen, 1427039636509332, 1, 15920, 15339⟩,
  ⟨11791, .fileSeen, 1427039636509332, 1, 15900, 15339⟩,
  ⟨11792, .fileSeen, 1427039636509332, 1, 15921, 15339⟩,
  ⟨11793, .fileSeen, 1427039636524932, 1, 15922, 15339⟩,
  ⟨11794, .fileSeen, 1427039636556132, 1, 15923, 15339⟩,
  ⟨11795, .fileSeen, 1427039636556132, 1, 15924, 15339⟩,
  ⟨11796, .fileSeen, 1427039636556132, 1, 15918, 15339⟩,
  ⟨11797, .fileSeen, 1427039636556132, 1, 15925, 15339⟩,
  ⟨11798, .fileSeen, 1427039636556132, 1, 15922, 15339⟩,
  ⟨11799, .fileSeen, 1427039636571732, 1, 15895, 15339⟩,
  ⟨11800, .fileSeen, 1427039636571732, 1, 15926, 15339⟩,
  ⟨11801, .fileSeen, 1427039638693336, 1, 15894, 15339⟩,
  ⟨11802, .fileSeen, 1427039638693336, 1, 15927, 15339⟩,
  ⟨11803, .fileSeen, 1427039640502939, 1, 15928, 15339⟩,
  ⟨11804, .fileSeen, 1427039640534139, 1, 15928, 15339⟩,
  ⟨11805, .fileSeen, 1427039640752540, 1, 15927, 15339⟩,
  ⟨11806, .fileSeen, 1427039640752540, 1, 15929, 15339⟩,
  ⟨11807, .fileSeen, 1427039641158140, 1, 15929, 15339⟩,
  ⟨11808, .fileSeen, 1427039642655743, 1, 15908, 15339⟩,
  ⟨11809, .fileSeen, 1427039642655743, 1, 15909, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11770) (.both (Sets.fileRecorded 11771) (.both (Sets.fileRecorded 11772) (.both (Sets.fileRecorded 11773) (.both (Sets.fileRecorded 11774) (.both (Sets.fileRecorded 11775) (.both (Sets.fileRecorded 11776) (.both (Sets.fileRecorded 11777) (.both (Sets.fileRecorded 11778) (.both (Sets.fileRecorded 11779) (.both (Sets.fileRecorded 11780) (.both (Sets.fileRecorded 11781) (.both (Sets.fileRecorded 11782) (.both (Sets.fileRecorded 11783) (.both (Sets.fileRecorded 11784) (.both (Sets.fileRecorded 11785) (.both (Sets.fileRecorded 11786) (.both (Sets.fileRecorded 11787) (.both (Sets.fileRecorded 11788) (.both (Sets.fileRecorded 11789) (.both (Sets.fileRecorded 11790) (.both (Sets.fileRecorded 11791) (.both (Sets.fileRecorded 11792) (.both (Sets.fileRecorded 11793) (.both (Sets.fileRecorded 11794) (.both (Sets.fileRecorded 11795) (.both (Sets.fileRecorded 11796) (.both (Sets.fileRecorded 11797) (.both (Sets.fileRecorded 11798) (.both (Sets.fileRecorded 11799) (.both (Sets.fileRecorded 11800) (.both (Sets.fileRecorded 11801) (.both (Sets.fileRecorded 11802) (.both (Sets.fileRecorded 11803) (.both (Sets.fileRecorded 11804) (.both (Sets.fileRecorded 11805) (.both (Sets.fileRecorded 11806) (.both (Sets.fileRecorded 11807) (.both (Sets.fileRecorded 11808) (Sets.fileRecorded 11809)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M310

#print axioms Cert.M310.verified
