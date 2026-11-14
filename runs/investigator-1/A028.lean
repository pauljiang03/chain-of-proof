import ChainOfProof
open ChainOfProof

namespace Cert.A028

def cited : List Fact := [
  ⟨1441, .programRun, 1427295476882005, 1, 1013, 1014⟩,
  ⟨1454, .programRun, 1427296550711000, 1, 773, 1027⟩,
  ⟨1455, .programRun, 1427296550711605, 1, 1028, 1029⟩ ]

def claim : Claim := .both (Sets.programRan 1441) (.both (Sets.programRan 1454) (Sets.programRan 1455))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A028

#print axioms Cert.A028.verified
