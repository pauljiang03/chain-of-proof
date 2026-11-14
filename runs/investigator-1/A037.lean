import ChainOfProof
open ChainOfProof

namespace Cert.A037

def cited : List Fact := [
  ⟨363, .webSearch, 1427231210726427, 1, 201, 159⟩ ]

def claim : Claim := Sets.searched 363

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A037

#print axioms Cert.A037.verified
