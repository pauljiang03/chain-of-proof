import ChainOfProof
open ChainOfProof

namespace Cert.A099

def cited : List Fact := [
  ⟨293, .webSearch, 1427294871248203, 1, 170, 126⟩,
  ⟨345, .tag, 1794614400000000, 1, 170, 195⟩ ]

def claim : Claim := Sets.tagged 293 .obj 345 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A099

#print axioms Cert.A099.verified
