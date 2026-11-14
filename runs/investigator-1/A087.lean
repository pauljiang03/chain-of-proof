import ChainOfProof
open ChainOfProof

namespace Cert.A087

def cited : List Fact := [
  ⟨12682, .shadowCopy, 1427295447293805, 1, 16117, 16118⟩,
  ⟨10082, .fileRenamed, 1427296419169805, 1, 13951, 13952⟩ ]

def claim : Claim := .before 12682 10082

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A087

#print axioms Cert.A087.verified
