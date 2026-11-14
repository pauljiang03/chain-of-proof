import ChainOfProof
open ChainOfProof

namespace Cert.M316

def cited : List Fact := [
  ⟨12010, .fileSeen, 1427039768413080, 1, 15995, 15545⟩,
  ⟨12011, .fileSeen, 1427039768413080, 1, 15808, 15545⟩,
  ⟨12012, .fileSeen, 1427039768428681, 1, 15954, 15339⟩,
  ⟨12013, .fileSeen, 1427039768428681, 1, 15996, 15339⟩,
  ⟨12014, .fileSeen, 1427039768475481, 1, 15476, 15339⟩,
  ⟨12015, .fileSeen, 1427039768475481, 1, 15997, 15339⟩,
  ⟨12016, .fileSeen, 1427039768491081, 1, 15996, 15339⟩,
  ⟨12017, .fileSeen, 1427039768491081, 1, 15475, 15339⟩,
  ⟨12018, .fileSeen, 1427039768506681, 1, 15996, 15339⟩,
  ⟨12019, .fileSeen, 1427039768506681, 1, 15997, 15339⟩,
  ⟨12020, .fileSeen, 1427039769051684, 1, 15953, 15339⟩,
  ⟨12021, .fileSeen, 1427039769051684, 1, 15977, 15339⟩,
  ⟨12022, .fileSeen, 1427039769061684, 1, 15956, 15339⟩,
  ⟨12023, .fileSeen, 1427039769065684, 1, 1458, 15339⟩,
  ⟨12024, .fileSeen, 1427039769165685, 1, 15954, 15339⟩,
  ⟨12025, .fileSeen, 1427039769197687, 1, 15996, 15339⟩,
  ⟨12026, .fileSeen, 1427039769217687, 1, 15987, 15339⟩,
  ⟨12027, .fileSeen, 1427039769217687, 1, 15955, 15339⟩,
  ⟨12028, .fileSeen, 1427039769232687, 1, 15957, 15339⟩,
  ⟨12029, .fileSeen, 1427039769236687, 1, 15958, 15339⟩,
  ⟨12030, .fileSeen, 1427039769240687, 1, 15961, 15339⟩,
  ⟨12031, .fileSeen, 1427039769244688, 1, 15959, 15339⟩,
  ⟨12032, .fileSeen, 1427039769248688, 1, 15968, 15339⟩,
  ⟨12033, .fileSeen, 1427039769269688, 1, 15475, 15339⟩,
  ⟨12034, .fileSeen, 1427039769289688, 1, 15476, 15339⟩,
  ⟨12035, .fileSeen, 1427039769299688, 1, 15997, 15339⟩,
  ⟨12036, .fileSeen, 1427039769299688, 1, 15983, 15339⟩,
  ⟨12037, .fileSeen, 1427039769309688, 1, 15984, 15339⟩,
  ⟨12038, .fileSeen, 1427039769319688, 1, 15985, 15339⟩,
  ⟨12039, .fileSeen, 1427039769329688, 1, 15986, 15339⟩,
  ⟨12040, .fileSeen, 1427039770045689, 1, 15982, 15339⟩,
  ⟨12041, .fileSeen, 1427039770061289, 1, 15989, 15339⟩,
  ⟨12042, .fileSeen, 1427039770076889, 1, 15970, 15339⟩,
  ⟨12043, .fileSeen, 1427039770076889, 1, 15967, 15339⟩,
  ⟨12044, .fileSeen, 1427039770092489, 1, 15979, 15339⟩,
  ⟨12045, .fileSeen, 1427039770092489, 1, 15988, 15339⟩,
  ⟨12046, .fileSeen, 1427039770092489, 1, 15980, 15339⟩,
  ⟨12047, .fileSeen, 1427039770092489, 1, 15981, 15339⟩,
  ⟨12048, .fileSeen, 1427039770108089, 1, 15972, 15339⟩,
  ⟨12049, .fileSeen, 1427039770108089, 1, 15975, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12010) (.both (Sets.fileRecorded 12011) (.both (Sets.fileRecorded 12012) (.both (Sets.fileRecorded 12013) (.both (Sets.fileRecorded 12014) (.both (Sets.fileRecorded 12015) (.both (Sets.fileRecorded 12016) (.both (Sets.fileRecorded 12017) (.both (Sets.fileRecorded 12018) (.both (Sets.fileRecorded 12019) (.both (Sets.fileRecorded 12020) (.both (Sets.fileRecorded 12021) (.both (Sets.fileRecorded 12022) (.both (Sets.fileRecorded 12023) (.both (Sets.fileRecorded 12024) (.both (Sets.fileRecorded 12025) (.both (Sets.fileRecorded 12026) (.both (Sets.fileRecorded 12027) (.both (Sets.fileRecorded 12028) (.both (Sets.fileRecorded 12029) (.both (Sets.fileRecorded 12030) (.both (Sets.fileRecorded 12031) (.both (Sets.fileRecorded 12032) (.both (Sets.fileRecorded 12033) (.both (Sets.fileRecorded 12034) (.both (Sets.fileRecorded 12035) (.both (Sets.fileRecorded 12036) (.both (Sets.fileRecorded 12037) (.both (Sets.fileRecorded 12038) (.both (Sets.fileRecorded 12039) (.both (Sets.fileRecorded 12040) (.both (Sets.fileRecorded 12041) (.both (Sets.fileRecorded 12042) (.both (Sets.fileRecorded 12043) (.both (Sets.fileRecorded 12044) (.both (Sets.fileRecorded 12045) (.both (Sets.fileRecorded 12046) (.both (Sets.fileRecorded 12047) (.both (Sets.fileRecorded 12048) (Sets.fileRecorded 12049)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M316

#print axioms Cert.M316.verified
