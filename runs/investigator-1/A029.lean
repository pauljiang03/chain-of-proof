import ChainOfProof
open ChainOfProof

namespace Cert.A029

def cited : List Fact := [
  ⟨1350, .programRun, 1427142410677000, 1, 735, 897⟩,
  ⟨1351, .programRun, 1427142453220000, 1, 741, 898⟩,
  ⟨1349, .programRun, 1427141419749000, 1, 567, 896⟩ ]

def claim : Claim := .both (Sets.programRan 1350) (.both (Sets.programRan 1351) (Sets.programRan 1349))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A029

#print axioms Cert.A029.verified
