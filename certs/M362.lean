import ChainOfProof
open ChainOfProof

namespace Cert.M362

def cited : List Fact := [
  ⟨269, .fileDeleted, 1427226707117000, 1, 144, 4⟩,
  ⟨270, .fileDeleted, 1427226707133000, 1, 145, 4⟩,
  ⟨271, .fileDeleted, 1427226707133000, 1, 146, 4⟩,
  ⟨272, .fileDeleted, 1427226707149000, 1, 147, 4⟩,
  ⟨273, .fileDeleted, 1427227902836000, 1, 148, 4⟩,
  ⟨274, .fileDeleted, 1427227902836000, 1, 149, 4⟩,
  ⟨275, .fileDeleted, 1427227902851000, 1, 150, 4⟩,
  ⟨276, .fileDeleted, 1427227902851000, 1, 151, 4⟩,
  ⟨277, .fileDeleted, 1427227902851000, 1, 152, 4⟩,
  ⟨278, .fileDeleted, 1427227902851000, 1, 153, 4⟩,
  ⟨279, .fileDeleted, 1427227902851000, 1, 154, 4⟩,
  ⟨280, .fileDeleted, 1427227902851000, 1, 155, 4⟩,
  ⟨281, .fileDeleted, 1427227902851000, 1, 156, 4⟩,
  ⟨282, .fileDeleted, 1427227902851000, 1, 157, 4⟩ ]

def census : Census := .total .fileDeleted 14

theorem verified : counts cited census = true := by decide +kernel

end Cert.M362

#print axioms Cert.M362.verified
