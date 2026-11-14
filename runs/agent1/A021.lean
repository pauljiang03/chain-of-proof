import ChainOfProof
open ChainOfProof

namespace Cert.A021

def cited : List Fact := [
  ⟨119, .webSearch, 1427131625838400, 1, 73, 69⟩ ]

def claim : Claim := Sets.searched 119

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A021

#print axioms Cert.A021.verified
