import ChainOfProof
open ChainOfProof

namespace Cert.A015

def cited : List Fact := [
  ⟨113, .webSearch, 1427037052000000, 1, 68, 69⟩ ]

def claim : Claim := Sets.searched 113

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A015

#print axioms Cert.A015.verified
