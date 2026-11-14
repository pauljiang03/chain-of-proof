import ChainOfProof
open ChainOfProof

namespace Cert.A182

def cited : List Fact := [
  ⟨40, .lnkTarget, 1427142457263674, 1, 28, 26⟩,
  ⟨2, .usbInsert, 1427204280014221, 1, 1, 0⟩ ]

def claim : Claim := .before 40 2

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A182

#print axioms Cert.A182.verified
