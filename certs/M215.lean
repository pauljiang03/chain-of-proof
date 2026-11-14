import ChainOfProof
open ChainOfProof

namespace Cert.M215

def cited : List Fact := [
  ⟨373, .emailSent, 1427138825282000, 1000000, 212, 208⟩ ]

def claim : Claim := Sets.emailed 373

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M215

#print axioms Cert.M215.verified
