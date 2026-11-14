import ChainOfProof
open ChainOfProof

namespace Cert.A004

def cited : List Fact := [
  ⟨542, .sessionEvent, 1427034868922289, 1, 297, 262⟩,
  ⟨710, .sessionEvent, 1427131481036285, 1, 297, 262⟩,
  ⟨754, .sessionEvent, 1427203304983509, 1, 297, 262⟩,
  ⟨768, .sessionEvent, 1427221718261791, 1, 297, 262⟩,
  ⟨832, .sessionEvent, 1427288768919298, 1, 297, 262⟩,
  ⟨848, .sessionEvent, 1427294759180204, 1, 297, 262⟩,
  ⟨860, .sessionEvent, 1427297457775204, 1, 301, 262⟩,
  ⟨869, .sessionEvent, 1427297465232008, 1, 298, 0⟩ ]

def claim : Claim := .both (Sets.sessionRecorded 542) (.both (Sets.sessionRecorded 710) (.both (Sets.sessionRecorded 754) (.both (Sets.sessionRecorded 768) (.both (Sets.sessionRecorded 832) (.both (Sets.sessionRecorded 848) (.both (Sets.sessionRecorded 860) (Sets.sessionRecorded 869)))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A004

#print axioms Cert.A004.verified
