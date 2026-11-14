import ChainOfProof
open ChainOfProof

namespace Cert.A025

def cited : List Fact := [
  ⟨123, .webSearch, 1427133797161615, 1, 75, 69⟩ ]

def claim : Claim := Sets.searched 123

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A025

#print axioms Cert.A025.verified
