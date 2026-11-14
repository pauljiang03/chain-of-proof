import ChainOfProof
open ChainOfProof

namespace Cert.A072

def cited : List Fact := [
  ⟨9000, .fileRenamed, 1427205188528464, 1, 12650, 12651⟩,
  ⟨9001, .fileRenamed, 1427205218854123, 1, 12652, 12653⟩,
  ⟨9002, .fileRenamed, 1427205232070747, 1, 12654, 12655⟩,
  ⟨8999, .fileRenamed, 1427205176999643, 1, 12648, 12649⟩,
  ⟨9004, .fileRenamed, 1427205263989414, 1, 12658, 12659⟩,
  ⟨9005, .fileRenamed, 1427205283133452, 1, 12660, 12661⟩,
  ⟨9006, .fileRenamed, 1427205292137070, 1, 12662, 12663⟩,
  ⟨9009, .fileRenamed, 1427205332087345, 1, 12666, 12667⟩,
  ⟨9010, .fileRenamed, 1427205342205365, 1, 12668, 12669⟩,
  ⟨9011, .fileRenamed, 1427205353633389, 1, 12670, 12671⟩,
  ⟨9012, .fileRenamed, 1427205369431423, 1, 12672, 12673⟩,
  ⟨9013, .fileRenamed, 1427205374509838, 1, 12674, 12675⟩,
  ⟨9014, .fileRenamed, 1427205380883054, 1, 12676, 12677⟩ ]

def claim : Claim := .both (Sets.renamed 9000) (.both (Sets.renamed 9001) (.both (Sets.renamed 9002) (.both (Sets.renamed 8999) (.both (Sets.renamed 9004) (.both (Sets.renamed 9005) (.both (Sets.renamed 9006) (.both (Sets.renamed 9009) (.both (Sets.renamed 9010) (.both (Sets.renamed 9011) (.both (Sets.renamed 9012) (.both (Sets.renamed 9013) (Sets.renamed 9014))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A072

#print axioms Cert.A072.verified
