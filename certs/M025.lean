import ChainOfProof
open ChainOfProof

namespace Cert.M025

def cited : List Fact := [
  ⟨42, .lnkTarget, 1427205689781835, 1, 32, 0⟩,
  ⟨334, .tag, 1794614400000000, 1, 32, 197⟩ ]

def claim : Claim := .both (Sets.opened 42) (Sets.tagged 42 .obj 334 197)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M025

#print axioms Cert.M025.verified
