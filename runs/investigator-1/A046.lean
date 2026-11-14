import ChainOfProof
open ChainOfProof

namespace Cert.A046

def cited : List Fact := [
  ⟨366, .webSearch, 1427294814471205, 1, 203, 160⟩,
  ⟨2267, .fileDownloaded, 1427294853852505, 1, 963, 1396⟩ ]

def claim : Claim := .before 366 2267

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A046

#print axioms Cert.A046.verified
