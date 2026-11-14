import ChainOfProof
open ChainOfProof

namespace Cert.M077

def cited : List Fact := [
  ⟨63, .fileCreated, 1247547263750120, 1, 48, 4⟩,
  ⟨172, .fileModified, 1247547264327320, 1, 48, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 63) (.both (Sets.fileModifiedAt 172) (.before 63 172))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M077

#print axioms Cert.M077.verified
