import ChainOfProof
open ChainOfProof

namespace Cert.M162

def cited : List Fact := [
  ⟨296, .emailSent, 1427138098000000, 1000000, 175, 172⟩ ]

def claim : Claim := Sets.emailed 296

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M162

#print axioms Cert.M162.verified
