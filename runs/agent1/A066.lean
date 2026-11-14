import ChainOfProof
open ChainOfProof

namespace Cert.A066

def cited : List Fact := [
  ⟨164, .webSearch, 1427140564087328, 1, 99, 69⟩ ]

def claim : Claim := Sets.searched 164

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A066

#print axioms Cert.A066.verified
