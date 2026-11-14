import ChainOfProof
open ChainOfProof

namespace Cert.M368

def cited : List Fact := [
  ⟨2271, .localSearch, 1427136017278767, 1, 1420, 1421⟩ ]

def census : Census := .total .localSearch 1

theorem verified : counts cited census = true := by decide +kernel

end Cert.M368

#print axioms Cert.M368.verified
