import ChainOfProof
open ChainOfProof

namespace Cert.A089

def cited : List Fact := [
  ⟨187, .webSearch, 1427144157412157, 1, 109, 70⟩ ]

def claim : Claim := Sets.searched 187

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A089

#print axioms Cert.A089.verified
