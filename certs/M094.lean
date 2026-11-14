import ChainOfProof
open ChainOfProof

namespace Cert.M094

def cited : List Fact := [
  ⟨80, .fileCreated, 1427039762282270, 1, 63, 4⟩,
  ⟨187, .fileModified, 1427039767040279, 1, 63, 4⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 80) (.both (Sets.fileModifiedAt 187) (.before 80 187))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M094

#print axioms Cert.M094.verified
