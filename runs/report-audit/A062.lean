import ChainOfProof
open ChainOfProof

namespace Cert.A062

def cited : List Fact := [
  ⟨160, .fileModified, 1418746226000000, 2000000, 93, 69⟩ ]

def claim : Claim := Sets.fileModifiedAt 160

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A062

#print axioms Cert.A062.verified
