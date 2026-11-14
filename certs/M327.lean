import ChainOfProof
open ChainOfProof

namespace Cert.M327

def cited : List Fact := [
  ⟨12450, .fileSeen, 1427221810908078, 1, 16082, 15339⟩,
  ⟨12451, .fileSeen, 1427221877089395, 1, 16083, 15339⟩,
  ⟨12452, .fileSeen, 1427221877292195, 1, 16081, 15339⟩,
  ⟨12453, .fileSeen, 1427222877879082, 1, 15548, 15339⟩,
  ⟨12454, .fileSeen, 1427222878253483, 1, 15548, 15339⟩,
  ⟨12455, .fileSeen, 1427222920734358, 1, 13034, 15339⟩,
  ⟨12456, .fileSeen, 1427222920749958, 1, 16084, 1549⟩,
  ⟨12457, .fileSeen, 1427222920827958, 1, 16085, 15453⟩,
  ⟨12458, .fileSeen, 1427222921202358, 1, 13034, 15339⟩,
  ⟨12459, .fileSeen, 1427222921311559, 1, 13034, 15339⟩,
  ⟨12460, .fileSeen, 1427222921342759, 1, 16086, 15453⟩,
  ⟨12461, .fileSeen, 1427222922278760, 1, 13034, 15339⟩,
  ⟨12462, .fileSeen, 1427223540000000, 60000000, 13034, 16011⟩,
  ⟨12463, .fileSeen, 1427223570579971, 1, 13034, 16011⟩,
  ⟨12464, .fileSeen, 1427224191987000, 1, 16007, 15453⟩,
  ⟨12465, .fileSeen, 1427224192003210, 1, 16085, 15453⟩,
  ⟨12466, .fileSeen, 1427224192736411, 1, 16086, 15453⟩,
  ⟨12467, .fileSeen, 1427224192736411, 1, 16010, 15453⟩,
  ⟨12468, .fileSeen, 1427224194265214, 1, 16087, 15453⟩,
  ⟨12469, .fileSeen, 1427225562000000, 1, 16088, 15339⟩,
  ⟨12470, .fileSeen, 1427225563185468, 1, 16088, 15339⟩,
  ⟨12471, .fileSeen, 1427225640000000, 1, 16089, 15339⟩,
  ⟨12472, .fileSeen, 1427225642420000, 1, 16088, 15339⟩,
  ⟨12473, .fileSeen, 1427225642435000, 1, 16089, 15339⟩,
  ⟨12474, .fileSeen, 1427225644198562, 1, 16088, 15339⟩,
  ⟨12475, .fileSeen, 1427225644432000, 1, 16089, 15339⟩,
  ⟨12476, .fileSeen, 1427225645508964, 1, 16089, 15339⟩,
  ⟨12477, .fileSeen, 1427226725744283, 1, 13125, 15339⟩,
  ⟨12478, .fileSeen, 1427226732452295, 1, 13125, 15339⟩,
  ⟨12479, .fileSeen, 1427226755727536, 1, 834, 15453⟩,
  ⟨12480, .fileSeen, 1427226755727536, 1, 834, 15339⟩,
  ⟨12481, .fileSeen, 1427226766800962, 1, 13951, 15453⟩,
  ⟨12482, .fileSeen, 1427226766800962, 1, 13951, 15339⟩,
  ⟨12483, .fileSeen, 1427226766816562, 1, 13957, 15453⟩,
  ⟨12484, .fileSeen, 1427226766816562, 1, 13957, 15339⟩,
  ⟨12485, .fileSeen, 1427226766816562, 1, 13965, 15453⟩,
  ⟨12486, .fileSeen, 1427226766816562, 1, 13965, 15339⟩,
  ⟨12487, .fileSeen, 1427226766832162, 1, 13980, 15453⟩,
  ⟨12488, .fileSeen, 1427226766832162, 1, 13980, 15339⟩,
  ⟨12489, .fileSeen, 1427226766832162, 1, 13988, 15453⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12450) (.both (Sets.fileRecorded 12451) (.both (Sets.fileRecorded 12452) (.both (Sets.fileRecorded 12453) (.both (Sets.fileRecorded 12454) (.both (Sets.fileRecorded 12455) (.both (Sets.fileRecorded 12456) (.both (Sets.fileRecorded 12457) (.both (Sets.fileRecorded 12458) (.both (Sets.fileRecorded 12459) (.both (Sets.fileRecorded 12460) (.both (Sets.fileRecorded 12461) (.both (Sets.fileRecorded 12462) (.both (Sets.fileRecorded 12463) (.both (Sets.fileRecorded 12464) (.both (Sets.fileRecorded 12465) (.both (Sets.fileRecorded 12466) (.both (Sets.fileRecorded 12467) (.both (Sets.fileRecorded 12468) (.both (Sets.fileRecorded 12469) (.both (Sets.fileRecorded 12470) (.both (Sets.fileRecorded 12471) (.both (Sets.fileRecorded 12472) (.both (Sets.fileRecorded 12473) (.both (Sets.fileRecorded 12474) (.both (Sets.fileRecorded 12475) (.both (Sets.fileRecorded 12476) (.both (Sets.fileRecorded 12477) (.both (Sets.fileRecorded 12478) (.both (Sets.fileRecorded 12479) (.both (Sets.fileRecorded 12480) (.both (Sets.fileRecorded 12481) (.both (Sets.fileRecorded 12482) (.both (Sets.fileRecorded 12483) (.both (Sets.fileRecorded 12484) (.both (Sets.fileRecorded 12485) (.both (Sets.fileRecorded 12486) (.both (Sets.fileRecorded 12487) (.both (Sets.fileRecorded 12488) (Sets.fileRecorded 12489)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M327

#print axioms Cert.M327.verified
