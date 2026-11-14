import ChainOfProof
open ChainOfProof

namespace Cert.A074

def cited : List Fact := [
  ⟨298, .emailSent, 1427138782000000, 1000000, 177, 172⟩,
  ⟨299, .emailSent, 1427138825282000, 1000000, 178, 174⟩ ]

def claim : Claim := .both (Sets.emailed 298) (.both (Sets.emailed 299) (.before 298 299))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A074

#print axioms Cert.A074.verified
