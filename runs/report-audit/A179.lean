import ChainOfProof
open ChainOfProof

namespace Cert.A179

def cited : List Fact := [
  ⟨298, .emailSent, 1427138782000000, 1000000, 177, 172⟩,
  ⟨299, .emailSent, 1427138825282000, 1000000, 178, 174⟩ ]

def claim : Claim := .before 298 299

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A179

#print axioms Cert.A179.verified
