import ChainOfProof
open ChainOfProof

namespace Cert.M039

def cited : List Fact := [
  ⟨123, .webSearch, 1427133797161615, 1, 75, 69⟩,
  ⟨233, .tag, 1794614400000000, 1, 75, 117⟩ ]

def claim : Claim := .both (Sets.searched 123) (Sets.tagged 123 .obj 233 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M039

#print axioms Cert.M039.verified
