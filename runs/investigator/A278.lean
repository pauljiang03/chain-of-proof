import ChainOfProof
open ChainOfProof

namespace Cert.A278

def cited : List Fact := [
  ⟨44, .lnkTarget, 1427229853752619, 1, 34, 35⟩,
  ⟨50, .lnkTarget, 1427230870763657, 1, 23, 40⟩ ]

def claim : Claim := .before 44 50

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A278

#print axioms Cert.A278.verified
