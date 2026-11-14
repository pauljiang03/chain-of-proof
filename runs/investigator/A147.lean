import ChainOfProof
open ChainOfProof

namespace Cert.A147

def cited : List Fact := [
  ⟨39, .lnkTarget, 1427142453345068, 1, 28, 26⟩ ]

def claim : Claim := Sets.opened 39

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A147

#print axioms Cert.A147.verified
