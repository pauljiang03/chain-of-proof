import ChainOfProof
open ChainOfProof

namespace Cert.M177

def cited : List Fact := [
  ⟨163, .fileCreated, 1427230623029598, 1, 43, 40⟩,
  ⟨177, .fileModified, 1247549551674540, 1, 43, 40⟩ ]

def claim : Claim := Sets.copiedHere 163 177

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M177

#print axioms Cert.M177.verified
