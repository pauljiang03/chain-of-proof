import ChainOfProof
open ChainOfProof

namespace Cert.A067

def cited : List Fact := [
  ⟨266, .webSearch, 1427143530137247, 1, 157, 126⟩ ]

def claim : Claim := Sets.searched 266

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A067

#print axioms Cert.A067.verified
