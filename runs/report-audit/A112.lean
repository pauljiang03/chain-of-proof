import ChainOfProof
open ChainOfProof

namespace Cert.A112

def cited : List Fact := [
  ⟨256, .webSearch, 1427134743860449, 1, 152, 125⟩ ]

def claim : Claim := Sets.searched 256

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A112

#print axioms Cert.A112.verified
