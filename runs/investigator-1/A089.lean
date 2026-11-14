import ChainOfProof
open ChainOfProof

namespace Cert.A089

def cited : List Fact := [
  ⟨10175, .fileRenamed, 1427296747365405, 1, 760, 14075⟩,
  ⟨10162, .fileRenamed, 1427296747334205, 1, 14050, 14051⟩,
  ⟨10152, .fileRenamed, 1427296747287405, 1, 14031, 14032⟩ ]

def claim : Claim := .both (Sets.renamed 10175) (.both (Sets.renamed 10162) (Sets.renamed 10152))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A089

#print axioms Cert.A089.verified
