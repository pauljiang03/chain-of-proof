import ChainOfProof
open ChainOfProof

namespace Cert.A078

def cited : List Fact := [
  ⟨176, .webSearch, 1427144110353085, 1, 104, 70⟩ ]

def claim : Claim := Sets.searched 176

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A078

#print axioms Cert.A078.verified
