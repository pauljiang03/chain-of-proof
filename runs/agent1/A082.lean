import ChainOfProof
open ChainOfProof

namespace Cert.A082

def cited : List Fact := [
  ⟨180, .webSearch, 1427144118340597, 1, 106, 70⟩ ]

def claim : Claim := Sets.searched 180

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A082

#print axioms Cert.A082.verified
