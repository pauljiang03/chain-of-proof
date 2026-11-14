import ChainOfProof
open ChainOfProof

namespace Cert.A099

def cited : List Fact := [
  ⟨197, .webSearch, 1427294871248203, 1, 114, 70⟩ ]

def claim : Claim := Sets.searched 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A099

#print axioms Cert.A099.verified
