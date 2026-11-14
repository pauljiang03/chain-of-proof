import ChainOfProof
open ChainOfProof

namespace Cert.A107

def cited : List Fact := [
  ⟨292, .webSearch, 1427294814471205, 1, 169, 126⟩,
  ⟨353, .tag, 1794614400000000, 1, 169, 195⟩ ]

def claim : Claim := Sets.tagged 292 .obj 353 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A107

#print axioms Cert.A107.verified
