import ChainOfProof
open ChainOfProof

namespace Cert.A002

def cited : List Fact := [
  ⟨522, .accountSeen, 1427034834422602, 1, 262, 288⟩,
  ⟨525, .accountSeen, 1427039514524311, 1, 291, 288⟩,
  ⟨527, .accountSeen, 1427039550742777, 1, 292, 288⟩,
  ⟨529, .accountSeen, 1427039581900034, 1, 293, 288⟩,
  ⟨532, .accountSeen, 1427279602864338, 1, 295, 288⟩,
  ⟨533, .accountSeen, 1427279602864338, 1, 296, 288⟩ ]

def claim : Claim := .both (Sets.accountRecorded 522) (.both (Sets.accountRecorded 525) (.both (Sets.accountRecorded 527) (.both (Sets.accountRecorded 529) (.both (Sets.accountRecorded 532) (Sets.accountRecorded 533)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A002

#print axioms Cert.A002.verified
