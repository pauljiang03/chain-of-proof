import ChainOfProof
open ChainOfProof

namespace Cert.A116

def cited : List Fact := [
  ⟨292, .webSearch, 1427294814471205, 1, 169, 126⟩ ]

def claim : Claim := Sets.searched 292

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A116

#print axioms Cert.A116.verified
