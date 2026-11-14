import ChainOfProof
open ChainOfProof

namespace Cert.M021

def cited : List Fact := [
  ⟨38, .lnkTarget, 1427142453345068, 1, 29, 26⟩,
  ⟨335, .tag, 1794614400000000, 1, 29, 197⟩ ]

def claim : Claim := .both (Sets.opened 38) (Sets.tagged 38 .obj 335 197)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M021

#print axioms Cert.M021.verified
