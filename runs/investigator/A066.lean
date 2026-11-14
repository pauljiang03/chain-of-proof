import ChainOfProof
open ChainOfProof

namespace Cert.A066

def cited : List Fact := [
  ⟨265, .webSearch, 1427143530127247, 1, 157, 126⟩ ]

def claim : Claim := Sets.searched 265

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A066

#print axioms Cert.A066.verified
