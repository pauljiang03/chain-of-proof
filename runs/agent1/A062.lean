import ChainOfProof
open ChainOfProof

namespace Cert.A062

def cited : List Fact := [
  ⟨160, .webSearch, 1427134743860449, 1, 96, 69⟩ ]

def claim : Claim := Sets.searched 160

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A062

#print axioms Cert.A062.verified
