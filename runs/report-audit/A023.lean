import ChainOfProof
open ChainOfProof

namespace Cert.A023

def cited : List Fact := [
  ⟨259, .webSearch, 1427140509975901, 1, 154, 125⟩,
  ⟨83, .fileCreated, 1427140547296776, 1, 66, 4⟩ ]

def claim : Claim := .before 259 83

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A023

#print axioms Cert.A023.verified
