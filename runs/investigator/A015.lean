import ChainOfProof
open ChainOfProof

namespace Cert.A015

def cited : List Fact := [
  ⟨214, .webSearch, 1427039744335028, 1, 128, 125⟩ ]

def claim : Claim := Sets.searched 214

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A015

#print axioms Cert.A015.verified
