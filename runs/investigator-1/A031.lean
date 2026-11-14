import ChainOfProof
open ChainOfProof

namespace Cert.A031

def cited : List Fact := [
  ⟨1451, .programRun, 1427296410777005, 1, 1021, 1022⟩,
  ⟨1455, .programRun, 1427296550711605, 1, 1028, 1029⟩ ]

def claim : Claim := .before 1451 1455

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A031

#print axioms Cert.A031.verified
