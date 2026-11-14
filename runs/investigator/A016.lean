import ChainOfProof
open ChainOfProof

namespace Cert.A016

def cited : List Fact := [
  ⟨215, .webSearch, 1427131625838400, 1, 129, 125⟩ ]

def claim : Claim := Sets.searched 215

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A016

#print axioms Cert.A016.verified
