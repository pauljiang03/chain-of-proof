import ChainOfProof
open ChainOfProof

namespace Cert.A275

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨125, .fileCreated, 1427222920734358, 1, 44, 4⟩ ]

def claim : Claim := .before 41 125

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A275

#print axioms Cert.A275.verified
