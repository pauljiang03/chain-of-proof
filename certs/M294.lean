import ChainOfProof
open ChainOfProof

namespace Cert.M294

def cited : List Fact := [
  ⟨11130, .fileSeen, 1427034876940703, 1, 15373, 15339⟩,
  ⟨11131, .fileSeen, 1427034876940703, 1, 15374, 15339⟩,
  ⟨11132, .fileSeen, 1427034876956303, 1, 15372, 15339⟩,
  ⟨11133, .fileSeen, 1427034876971903, 1, 15340, 15339⟩,
  ⟨11134, .fileSeen, 1427034876971903, 1, 15341, 15339⟩,
  ⟨11135, .fileSeen, 1427034876987503, 1, 15338, 15339⟩,
  ⟨11136, .fileSeen, 1427034876987503, 1, 15464, 15339⟩,
  ⟨11137, .fileSeen, 1427034877798704, 1, 15399, 15339⟩,
  ⟨11138, .fileSeen, 1427034877814304, 1, 15398, 15339⟩,
  ⟨11139, .fileSeen, 1427034877814304, 1, 15396, 15339⟩,
  ⟨11140, .fileSeen, 1427034877814304, 1, 15407, 15339⟩,
  ⟨11141, .fileSeen, 1427034877814304, 1, 15394, 15339⟩,
  ⟨11142, .fileSeen, 1427034877829904, 1, 15403, 15339⟩,
  ⟨11143, .fileSeen, 1427034877829904, 1, 15391, 15339⟩,
  ⟨11144, .fileSeen, 1427034877829904, 1, 15468, 15339⟩,
  ⟨11145, .fileSeen, 1427034877829904, 1, 15465, 15339⟩,
  ⟨11146, .fileSeen, 1427034877829904, 1, 15405, 15339⟩,
  ⟨11147, .fileSeen, 1427034877845504, 1, 15392, 15339⟩,
  ⟨11148, .fileSeen, 1427034877845504, 1, 15400, 15339⟩,
  ⟨11149, .fileSeen, 1427034877845504, 1, 15401, 15339⟩,
  ⟨11150, .fileSeen, 1427034881168310, 1, 15484, 15453⟩,
  ⟨11151, .fileSeen, 1427034881168310, 1, 15484, 15339⟩,
  ⟨11152, .fileSeen, 1427034881183910, 1, 15485, 15339⟩,
  ⟨11153, .fileSeen, 1427034881183910, 1, 15486, 15339⟩,
  ⟨11154, .fileSeen, 1427034881183910, 1, 15487, 15339⟩,
  ⟨11155, .fileSeen, 1427034881183910, 1, 15488, 15339⟩,
  ⟨11156, .fileSeen, 1427034881230710, 1, 15489, 15339⟩,
  ⟨11157, .fileSeen, 1427034881230710, 1, 15490, 15339⟩,
  ⟨11158, .fileSeen, 1427034881246310, 1, 15491, 15339⟩,
  ⟨11159, .fileSeen, 1427034881246310, 1, 15492, 15339⟩,
  ⟨11160, .fileSeen, 1427034881246310, 1, 15493, 15339⟩,
  ⟨11161, .fileSeen, 1427034881246310, 1, 15494, 15339⟩,
  ⟨11162, .fileSeen, 1427034881386710, 1, 15495, 15339⟩,
  ⟨11163, .fileSeen, 1427034881386710, 1, 15496, 15339⟩,
  ⟨11164, .fileSeen, 1427034881386710, 1, 15497, 15453⟩,
  ⟨11165, .fileSeen, 1427034881386710, 1, 15497, 15339⟩,
  ⟨11166, .fileSeen, 1427034881386710, 1, 15498, 15339⟩,
  ⟨11167, .fileSeen, 1427034881402310, 1, 15499, 15339⟩,
  ⟨11168, .fileSeen, 1427034881433511, 1, 15491, 15339⟩,
  ⟨11169, .fileSeen, 1427034881433511, 1, 15500, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11130) (.both (Sets.fileRecorded 11131) (.both (Sets.fileRecorded 11132) (.both (Sets.fileRecorded 11133) (.both (Sets.fileRecorded 11134) (.both (Sets.fileRecorded 11135) (.both (Sets.fileRecorded 11136) (.both (Sets.fileRecorded 11137) (.both (Sets.fileRecorded 11138) (.both (Sets.fileRecorded 11139) (.both (Sets.fileRecorded 11140) (.both (Sets.fileRecorded 11141) (.both (Sets.fileRecorded 11142) (.both (Sets.fileRecorded 11143) (.both (Sets.fileRecorded 11144) (.both (Sets.fileRecorded 11145) (.both (Sets.fileRecorded 11146) (.both (Sets.fileRecorded 11147) (.both (Sets.fileRecorded 11148) (.both (Sets.fileRecorded 11149) (.both (Sets.fileRecorded 11150) (.both (Sets.fileRecorded 11151) (.both (Sets.fileRecorded 11152) (.both (Sets.fileRecorded 11153) (.both (Sets.fileRecorded 11154) (.both (Sets.fileRecorded 11155) (.both (Sets.fileRecorded 11156) (.both (Sets.fileRecorded 11157) (.both (Sets.fileRecorded 11158) (.both (Sets.fileRecorded 11159) (.both (Sets.fileRecorded 11160) (.both (Sets.fileRecorded 11161) (.both (Sets.fileRecorded 11162) (.both (Sets.fileRecorded 11163) (.both (Sets.fileRecorded 11164) (.both (Sets.fileRecorded 11165) (.both (Sets.fileRecorded 11166) (.both (Sets.fileRecorded 11167) (.both (Sets.fileRecorded 11168) (Sets.fileRecorded 11169)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M294

#print axioms Cert.M294.verified
