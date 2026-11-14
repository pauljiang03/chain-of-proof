import ChainOfProof
open ChainOfProof

namespace Cert.A032

def cited : List Fact := [
  ⟨1409, .programRun, 1427295014393805, 1, 966, 967⟩,
  ⟨1451, .programRun, 1427296410777005, 1, 1021, 1022⟩ ]

def claim : Claim := .before 1409 1451

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A032

#print axioms Cert.A032.verified
