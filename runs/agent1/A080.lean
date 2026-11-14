import ChainOfProof
open ChainOfProof

namespace Cert.A080

def cited : List Fact := [
  ⟨178, .webSearch, 1427144117475595, 1, 105, 70⟩ ]

def claim : Claim := Sets.searched 178

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A080

#print axioms Cert.A080.verified
