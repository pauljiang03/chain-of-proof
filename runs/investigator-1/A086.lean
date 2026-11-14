import ChainOfProof
open ChainOfProof

namespace Cert.A086

def cited : List Fact := [
  ⟨1449, .programRun, 1427296348735000, 1, 763, 1018⟩,
  ⟨10082, .fileRenamed, 1427296419169805, 1, 13951, 13952⟩ ]

def claim : Claim := .before 1449 10082

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A086

#print axioms Cert.A086.verified
