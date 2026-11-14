import ChainOfProof
open ChainOfProof

namespace Cert.A040

def cited : List Fact := [
  ⟨239, .webSearch, 1427134203820419, 1, 139, 126⟩ ]

def claim : Claim := Sets.searched 239

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A040

#print axioms Cert.A040.verified
