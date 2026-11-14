import ChainOfProof
open ChainOfProof

namespace Cert.M039

def cited : List Fact := [
  ⟨219, .webSearch, 1427133797161615, 1, 131, 125⟩,
  ⟨361, .tag, 1794614400000000, 1, 131, 195⟩ ]

def claim : Claim := .both (Sets.searched 219) (Sets.tagged 219 .obj 361 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M039

#print axioms Cert.M039.verified
