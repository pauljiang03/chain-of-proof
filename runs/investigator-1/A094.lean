import ChainOfProof
open ChainOfProof

namespace Cert.A094

def cited : List Fact := [
  ⟨8130, .fileRenamed, 1427135943459437, 1, 12119, 12120⟩,
  ⟨8134, .fileRenamed, 1427136100269314, 1, 12121, 12122⟩ ]

def claim : Claim := .both (Sets.renamed 8130) (Sets.renamed 8134)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A094

#print axioms Cert.A094.verified
