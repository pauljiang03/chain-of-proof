import ChainOfProof
open ChainOfProof

namespace Cert.M370

def cited : List Fact := [
  ⟨2309, .noteText, 1427221877057999, 1, 1431, 1432⟩,
  ⟨2310, .noteText, 1427221919462999, 1, 1431, 1432⟩ ]

def census : Census := .total .noteText 2

theorem verified : counts cited census = true := by decide +kernel

end Cert.M370

#print axioms Cert.M370.verified
