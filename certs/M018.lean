import ChainOfProof
open ChainOfProof

namespace Cert.M018

def cited : List Fact := [
  ⟨35, .lnkTarget, 1427142416032196, 1, 25, 26⟩,
  ⟨214, .tag, 1794614400000000, 1, 25, 118⟩ ]

def claim : Claim := .both (Sets.opened 35) (Sets.tagged 35 .obj 214 118)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M018

#print axioms Cert.M018.verified
