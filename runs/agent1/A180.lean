import ChainOfProof
open ChainOfProof

namespace Cert.A180

def cited : List Fact := [
  ⟨163, .webSearch, 1427140509975901, 1, 98, 69⟩,
  ⟨83, .fileCreated, 1427140547296776, 1, 66, 4⟩ ]

def claim : Claim := .before 163 83

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A180

#print axioms Cert.A180.verified
