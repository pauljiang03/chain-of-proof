import ChainOfProof
open ChainOfProof

namespace Cert.A090

def cited : List Fact := [
  ⟨289, .webSearch, 1427231210726427, 1, 167, 125⟩ ]

def claim : Claim := Sets.searched 289

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A090

#print axioms Cert.A090.verified
