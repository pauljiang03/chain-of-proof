import ChainOfProof
open ChainOfProof

namespace Cert.A078

def cited : List Fact := [
  ⟨277, .webSearch, 1427144129240612, 1, 156, 126⟩ ]

def claim : Claim := Sets.searched 277

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A078

#print axioms Cert.A078.verified
