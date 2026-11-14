import ChainOfProof
open ChainOfProof

namespace Cert.A088

def cited : List Fact := [
  ⟨10144, .fileRenamed, 1427296429637405, 1, 13125, 14020⟩,
  ⟨1455, .programRun, 1427296550711605, 1, 1028, 1029⟩ ]

def claim : Claim := .before 10144 1455

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A088

#print axioms Cert.A088.verified
