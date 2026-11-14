import ChainOfProof
open ChainOfProof

namespace Cert.A032

def cited : List Fact := [
  ⟨130, .webSearch, 1427133922229486, 1, 76, 69⟩ ]

def claim : Claim := Sets.searched 130

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A032

#print axioms Cert.A032.verified
