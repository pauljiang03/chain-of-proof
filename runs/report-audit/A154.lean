import ChainOfProof
open ChainOfProof

namespace Cert.A154

def cited : List Fact := [
  ⟨163, .fileModified, 1419018826000000, 10000, 18, 19⟩,
  ⟨332, .tag, 1794614400000000, 1, 18, 201⟩ ]

def claim : Claim := Sets.tagged 163 .obj 332 201

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A154

#print axioms Cert.A154.verified
