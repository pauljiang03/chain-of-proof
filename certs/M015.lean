import ChainOfProof
open ChainOfProof

namespace Cert.M015

def cited : List Fact := [
  ⟨32, .lnkTarget, 1427142413924193, 1, 27, 26⟩,
  ⟨213, .tag, 1794614400000000, 1, 27, 118⟩ ]

def claim : Claim := .both (Sets.opened 32) (Sets.tagged 32 .obj 213 118)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M015

#print axioms Cert.M015.verified
