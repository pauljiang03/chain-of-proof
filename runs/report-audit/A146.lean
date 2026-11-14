import ChainOfProof
open ChainOfProof

namespace Cert.A146

def cited : List Fact := [
  ⟨176, .fileModified, 1422046030000000, 10000, 52, 19⟩,
  ⟨327, .tag, 1794614400000000, 1, 52, 199⟩ ]

def claim : Claim := Sets.tagged 176 .obj 327 199

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A146

#print axioms Cert.A146.verified
