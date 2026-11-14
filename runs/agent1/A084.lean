import ChainOfProof
open ChainOfProof

namespace Cert.A084

def cited : List Fact := [
  ⟨182, .webSearch, 1427144129265612, 1, 100, 70⟩ ]

def claim : Claim := Sets.searched 182

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A084

#print axioms Cert.A084.verified
