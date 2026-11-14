import ChainOfProof
open ChainOfProof

namespace Cert.M014

def cited : List Fact := [
  ⟨31, .lnkTarget, 1427142413783793, 1, 25, 26⟩,
  ⟨214, .tag, 1794614400000000, 1, 25, 118⟩ ]

def claim : Claim := .both (Sets.opened 31) (Sets.tagged 31 .obj 214 118)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M014

#print axioms Cert.M014.verified
