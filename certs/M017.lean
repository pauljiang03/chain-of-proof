import ChainOfProof
open ChainOfProof

namespace Cert.M017

def cited : List Fact := [
  ⟨34, .lnkTarget, 1427142414002193, 1, 27, 26⟩,
  ⟨337, .tag, 1794614400000000, 1, 27, 197⟩ ]

def claim : Claim := .both (Sets.opened 34) (Sets.tagged 34 .obj 337 197)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M017

#print axioms Cert.M017.verified
