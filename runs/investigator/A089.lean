import ChainOfProof
open ChainOfProof

namespace Cert.A089

def cited : List Fact := [
  ⟨288, .webSearch, 1427144278459051, 1, 158, 126⟩ ]

def claim : Claim := Sets.searched 288

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A089

#print axioms Cert.A089.verified
