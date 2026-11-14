import ChainOfProof
open ChainOfProof

namespace Cert.A148

def cited : List Fact := [
  ⟨60, .lnkTarget, 1427297348981604, 1, 44, 4⟩ ]

def claim : Claim := Sets.opened 60

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A148

#print axioms Cert.A148.verified
