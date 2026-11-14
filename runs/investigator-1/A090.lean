import ChainOfProof
open ChainOfProof

namespace Cert.A090

def cited : List Fact := [
  ⟨1455, .programRun, 1427296550711605, 1, 1028, 1029⟩,
  ⟨10175, .fileRenamed, 1427296747365405, 1, 760, 14075⟩ ]

def claim : Claim := .before 1455 10175

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A090

#print axioms Cert.A090.verified
