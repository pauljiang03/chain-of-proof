import ChainOfProof
open ChainOfProof

namespace Cert.A070

def cited : List Fact := [
  ⟨168, .webSearch, 1427143522377234, 1, 100, 70⟩ ]

def claim : Claim := Sets.searched 168

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A070

#print axioms Cert.A070.verified
