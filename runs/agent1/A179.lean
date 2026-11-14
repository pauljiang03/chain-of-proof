import ChainOfProof
open ChainOfProof

namespace Cert.A179

def cited : List Fact := [
  ⟨151, .webSearch, 1427134490369135, 1, 90, 69⟩,
  ⟨83, .fileCreated, 1427140547296776, 1, 66, 4⟩ ]

def claim : Claim := .before 151 83

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A179

#print axioms Cert.A179.verified
