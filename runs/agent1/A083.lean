import ChainOfProof
open ChainOfProof

namespace Cert.A083

def cited : List Fact := [
  ⟨181, .webSearch, 1427144129240612, 1, 100, 70⟩ ]

def claim : Claim := Sets.searched 181

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A083

#print axioms Cert.A083.verified
