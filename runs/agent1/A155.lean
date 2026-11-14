import ChainOfProof
open ChainOfProof

namespace Cert.A155

def cited : List Fact := [
  ⟨140, .webSearch, 1427134111817280, 1, 81, 70⟩,
  ⟨200, .tag, 1794614400000000, 1, 81, 117⟩ ]

def claim : Claim := Sets.tagged 140 .obj 200 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A155

#print axioms Cert.A155.verified
