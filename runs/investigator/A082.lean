import ChainOfProof
open ChainOfProof

namespace Cert.A082

def cited : List Fact := [
  ⟨281, .webSearch, 1427144156134653, 1, 164, 126⟩ ]

def claim : Claim := Sets.searched 281

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A082

#print axioms Cert.A082.verified
