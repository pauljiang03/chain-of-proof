import ChainOfProof
open ChainOfProof

namespace Cert.A210

def cited : List Fact := [
  ⟨122, .fileCreated, 1427205614340000, 10000, 106, 69⟩,
  ⟨170, .fileModified, 1421090426000000, 2000000, 106, 69⟩ ]

def claim : Claim := Sets.copiedHere 122 170

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A210

#print axioms Cert.A210.verified
