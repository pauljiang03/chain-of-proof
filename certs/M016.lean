import ChainOfProof
open ChainOfProof

namespace Cert.M016

def cited : List Fact := [
  ⟨33, .lnkTarget, 1427142413986593, 1, 25, 26⟩,
  ⟨412, .tag, 1794614400000000, 1, 25, 231⟩ ]

def claim : Claim := .both (Sets.opened 33) (Sets.tagged 33 .obj 412 231)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M016

#print axioms Cert.M016.verified
