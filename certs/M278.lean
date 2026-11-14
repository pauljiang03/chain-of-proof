import ChainOfProof
open ChainOfProof

namespace Cert.M278

def cited : List Fact := [
  ⟨2271, .localSearch, 1427136017278767, 1, 1420, 1421⟩ ]

def claim : Claim := Sets.typedInSearchBox 2271

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M278

#print axioms Cert.M278.verified
