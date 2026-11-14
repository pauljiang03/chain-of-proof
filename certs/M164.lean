import ChainOfProof
open ChainOfProof

namespace Cert.M164

def cited : List Fact := [
  ⟨298, .emailSent, 1427138782000000, 1000000, 177, 172⟩ ]

def claim : Claim := Sets.emailed 298

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M164

#print axioms Cert.M164.verified
