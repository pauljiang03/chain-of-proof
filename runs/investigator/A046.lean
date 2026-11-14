import ChainOfProof
open ChainOfProof

namespace Cert.A046

def cited : List Fact := [
  ⟨245, .webSearch, 1427134438392908, 1, 136, 126⟩ ]

def claim : Claim := Sets.searched 245

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A046

#print axioms Cert.A046.verified
