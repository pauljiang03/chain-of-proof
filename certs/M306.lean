import ChainOfProof
open ChainOfProof

namespace Cert.M306

def cited : List Fact := [
  ⟨11610, .fileSeen, 1427034908022357, 1, 15520, 15339⟩,
  ⟨11611, .fileSeen, 1427034908037958, 1, 15521, 15339⟩,
  ⟨11612, .fileSeen, 1427034908131558, 1, 15517, 15339⟩,
  ⟨11613, .fileSeen, 1427034908147158, 1, 15518, 15339⟩,
  ⟨11614, .fileSeen, 1427034908162758, 1, 15512, 15339⟩,
  ⟨11615, .fileSeen, 1427034908162758, 1, 15515, 15339⟩,
  ⟨11616, .fileSeen, 1427034908162758, 1, 15510, 15339⟩,
  ⟨11617, .fileSeen, 1427034908162758, 1, 15511, 15339⟩,
  ⟨11618, .fileSeen, 1427034908162758, 1, 15516, 15339⟩,
  ⟨11619, .fileSeen, 1427034908162758, 1, 15514, 15339⟩,
  ⟨11620, .fileSeen, 1427034908178358, 1, 15507, 15339⟩,
  ⟨11621, .fileSeen, 1427034908178358, 1, 15509, 15339⟩,
  ⟨11622, .fileSeen, 1427034908178358, 1, 15508, 15339⟩,
  ⟨11623, .fileSeen, 1427034908178358, 1, 15506, 15339⟩,
  ⟨11624, .fileSeen, 1427034911079963, 1, 15504, 15339⟩,
  ⟨11625, .fileSeen, 1427035043259796, 1, 15845, 15453⟩,
  ⟨11626, .fileSeen, 1427035093977285, 1, 15846, 15453⟩,
  ⟨11627, .fileSeen, 1427035095919289, 1, 15495, 15339⟩,
  ⟨11628, .fileSeen, 1427035095919289, 1, 15496, 15339⟩,
  ⟨11629, .fileSeen, 1427035095919289, 1, 15499, 15339⟩,
  ⟨11630, .fileSeen, 1427036195754591, 1, 15498, 15339⟩,
  ⟨11631, .fileSeen, 1427036197501794, 1, 15500, 15339⟩,
  ⟨11632, .fileSeen, 1427036197657794, 1, 15495, 15339⟩,
  ⟨11633, .fileSeen, 1427036197673394, 1, 15496, 15339⟩,
  ⟨11634, .fileSeen, 1427036197673394, 1, 15499, 15339⟩,
  ⟨11635, .fileSeen, 1427036609107118, 1, 15847, 15339⟩,
  ⟨11636, .fileSeen, 1427036609107118, 1, 15848, 15339⟩,
  ⟨11637, .fileSeen, 1427036609185118, 1, 15849, 15339⟩,
  ⟨11638, .fileSeen, 1427036609325518, 1, 15849, 15339⟩,
  ⟨11639, .fileSeen, 1427036609341118, 1, 15850, 15339⟩,
  ⟨11640, .fileSeen, 1427036609341118, 1, 15851, 15339⟩,
  ⟨11641, .fileSeen, 1427036609356718, 1, 15852, 15339⟩,
  ⟨11642, .fileSeen, 1427036609356718, 1, 15853, 15339⟩,
  ⟨11643, .fileSeen, 1427036609356718, 1, 15850, 15339⟩,
  ⟨11644, .fileSeen, 1427036609372318, 1, 15852, 15339⟩,
  ⟨11645, .fileSeen, 1427036609372318, 1, 15854, 15339⟩,
  ⟨11646, .fileSeen, 1427036609372318, 1, 15855, 15339⟩,
  ⟨11647, .fileSeen, 1427036609387918, 1, 15848, 15339⟩,
  ⟨11648, .fileSeen, 1427036609387918, 1, 15854, 15339⟩,
  ⟨11649, .fileSeen, 1427036609387918, 1, 15856, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11610) (.both (Sets.fileRecorded 11611) (.both (Sets.fileRecorded 11612) (.both (Sets.fileRecorded 11613) (.both (Sets.fileRecorded 11614) (.both (Sets.fileRecorded 11615) (.both (Sets.fileRecorded 11616) (.both (Sets.fileRecorded 11617) (.both (Sets.fileRecorded 11618) (.both (Sets.fileRecorded 11619) (.both (Sets.fileRecorded 11620) (.both (Sets.fileRecorded 11621) (.both (Sets.fileRecorded 11622) (.both (Sets.fileRecorded 11623) (.both (Sets.fileRecorded 11624) (.both (Sets.fileRecorded 11625) (.both (Sets.fileRecorded 11626) (.both (Sets.fileRecorded 11627) (.both (Sets.fileRecorded 11628) (.both (Sets.fileRecorded 11629) (.both (Sets.fileRecorded 11630) (.both (Sets.fileRecorded 11631) (.both (Sets.fileRecorded 11632) (.both (Sets.fileRecorded 11633) (.both (Sets.fileRecorded 11634) (.both (Sets.fileRecorded 11635) (.both (Sets.fileRecorded 11636) (.both (Sets.fileRecorded 11637) (.both (Sets.fileRecorded 11638) (.both (Sets.fileRecorded 11639) (.both (Sets.fileRecorded 11640) (.both (Sets.fileRecorded 11641) (.both (Sets.fileRecorded 11642) (.both (Sets.fileRecorded 11643) (.both (Sets.fileRecorded 11644) (.both (Sets.fileRecorded 11645) (.both (Sets.fileRecorded 11646) (.both (Sets.fileRecorded 11647) (.both (Sets.fileRecorded 11648) (Sets.fileRecorded 11649)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M306

#print axioms Cert.M306.verified
