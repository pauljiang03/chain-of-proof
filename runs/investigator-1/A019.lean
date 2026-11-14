import ChainOfProof
open ChainOfProof

namespace Cert.A019

def cited : List Fact := [
  ⟨66, .fileCreated, 1424037128960000, 10000, 22, 19⟩,
  ⟨67, .fileCreated, 1424037129290000, 10000, 51, 19⟩,
  ⟨68, .fileCreated, 1424037130630000, 10000, 52, 19⟩,
  ⟨69, .fileCreated, 1424037132550000, 10000, 53, 19⟩,
  ⟨70, .fileCreated, 1424037140430000, 10000, 18, 19⟩ ]

def claim : Claim := .both (Sets.fileCreatedAt 66) (.both (Sets.fileCreatedAt 67) (.both (Sets.fileCreatedAt 68) (.both (Sets.fileCreatedAt 69) (Sets.fileCreatedAt 70))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A019

#print axioms Cert.A019.verified
