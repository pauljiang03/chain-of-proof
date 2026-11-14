import ChainOfProof
open ChainOfProof

namespace Cert.M173

def cited : List Fact := [
  ⟨307, .cdBurn, 1427226961607515, 1, 188, 185⟩ ]

def claim : Claim := Sets.burnTrace 307

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M173

#print axioms Cert.M173.verified
