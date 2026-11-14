import ChainOfProof
open ChainOfProof

namespace Cert.A147

def cited : List Fact := [
  ⟨59, .lnkTarget, 1427297348934805, 1, 44, 4⟩ ]

def claim : Claim := Sets.opened 59

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A147

#print axioms Cert.A147.verified
