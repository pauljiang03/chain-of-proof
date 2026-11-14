import ChainOfProof
open ChainOfProof

namespace Cert.A084

def cited : List Fact := [
  ⟨12639, .fileSeen, 1427295447293805, 1, 13951, 15453⟩,
  ⟨12640, .fileSeen, 1427295447293805, 1, 13957, 15453⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12639) (Sets.fileRecorded 12640)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A084

#print axioms Cert.A084.verified
