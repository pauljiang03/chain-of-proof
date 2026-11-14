import ChainOfProof
open ChainOfProof

namespace Cert.A173

def cited : List Fact := [
  ⟨295, .emailSent, 1427136271719000, 1000000, 173, 174⟩ ]

def claim : Claim := Sets.emailed 295

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A173

#print axioms Cert.A173.verified
