import ChainOfProof
open ChainOfProof

namespace Cert.A085

def cited : List Fact := [
  ⟨10082, .fileRenamed, 1427296419169805, 1, 13951, 13952⟩,
  ⟨10084, .fileRenamed, 1427296419169805, 1, 13952, 13953⟩,
  ⟨10102, .fileRenamed, 1427296428685805, 1, 834, 13974⟩,
  ⟨10144, .fileRenamed, 1427296429637405, 1, 13125, 14020⟩,
  ⟨10143, .fileRenamed, 1427296429637405, 1, 14020, 14018⟩ ]

def claim : Claim := .both (Sets.renamed 10082) (.both (Sets.renamed 10084) (.both (Sets.renamed 10102) (.both (Sets.renamed 10144) (Sets.renamed 10143))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A085

#print axioms Cert.A085.verified
