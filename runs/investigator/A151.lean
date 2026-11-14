import ChainOfProof
open ChainOfProof

namespace Cert.A151

def cited : List Fact := [
  ⟨32, .lnkTarget, 1427142413924193, 1, 27, 26⟩,
  ⟨337, .tag, 1794614400000000, 1, 27, 197⟩ ]

def claim : Claim := Sets.tagged 32 .obj 337 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A151

#print axioms Cert.A151.verified
