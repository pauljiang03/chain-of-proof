import ChainOfProof
open ChainOfProof

namespace Cert.M039

def cited : List Fact := [
  ⟨293, .webSearch, 1427133797161615, 1, 165, 159⟩,
  ⟨483, .tag, 1794614400000000, 1, 165, 229⟩ ]

def claim : Claim := .both (Sets.searched 293) (Sets.tagged 293 .obj 483 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M039

#print axioms Cert.M039.verified
