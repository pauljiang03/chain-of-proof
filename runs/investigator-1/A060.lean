import ChainOfProof
open ChainOfProof

namespace Cert.A060

def cited : List Fact := [
  ⟨8981, .fileRenamed, 1427204991896881, 1, 12620, 12621⟩,
  ⟨8982, .fileRenamed, 1427205008118110, 1, 12622, 12623⟩,
  ⟨9007, .fileRenamed, 1427205308808901, 1, 12632, 12664⟩,
  ⟨9008, .fileRenamed, 1427205317047716, 1, 12627, 12665⟩,
  ⟨9003, .fileRenamed, 1427205245485773, 1, 12656, 12657⟩,
  ⟨8998, .fileRenamed, 1427205155708597, 1, 12646, 12647⟩ ]

def claim : Claim := .both (Sets.renamed 8981) (.both (Sets.renamed 8982) (.both (Sets.renamed 9007) (.both (Sets.renamed 9008) (.both (Sets.renamed 9003) (Sets.renamed 8998)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A060

#print axioms Cert.A060.verified
