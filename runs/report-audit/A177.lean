import ChainOfProof
open ChainOfProof

namespace Cert.A177

def cited : List Fact := [
  ⟨298, .emailSent, 1427138782000000, 1000000, 177, 172⟩ ]

def claim : Claim := Sets.emailed 298

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A177

#print axioms Cert.A177.verified
