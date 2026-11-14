import ChainOfProof
open ChainOfProof

namespace Cert.A026

def cited : List Fact := [
  ⟨982, .programInstalled, 1427140966000000, 1000000, 351, 352⟩,
  ⟨980, .programInstalled, 1427140914337250, 1, 353, 354⟩,
  ⟨1344, .programRun, 1427140593481297, 1, 765, 889⟩,
  ⟨1345, .programRun, 1427140613339270, 1, 890, 891⟩,
  ⟨1496, .programRun, 1427296891899405, 1, 1078, 1079⟩ ]

def claim : Claim := .both (Sets.programInstalledAt 982) (.both (Sets.programInstalledAt 980) (.both (Sets.programRan 1344) (.both (Sets.programRan 1345) (Sets.programRan 1496))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A026

#print axioms Cert.A026.verified
