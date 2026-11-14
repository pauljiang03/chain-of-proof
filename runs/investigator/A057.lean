import ChainOfProof
open ChainOfProof

namespace Cert.A057

def cited : List Fact := [
  ⟨256, .webSearch, 1427134743860449, 1, 152, 125⟩ ]

def claim : Claim := Sets.searched 256

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A057

#print axioms Cert.A057.verified
