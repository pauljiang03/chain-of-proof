import ChainOfProof
open ChainOfProof

namespace Cert.M214

def cited : List Fact := [
  ⟨372, .emailSent, 1427138782000000, 1000000, 211, 206⟩ ]

def claim : Claim := Sets.emailed 372

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M214

#print axioms Cert.M214.verified
