import ChainOfProof
open ChainOfProof

namespace Cert.M096

def cited : List Fact := [
  ⟨82, .fileCreated, 1427039762329069, 1, 65, 4⟩,
  ⟨107, .fileModified, 1427039767055880, 1, 65, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 82) (.both (Sets.fileModifiedAt 107) (.before 82 107))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M096

#print axioms Cert.M096.verified
