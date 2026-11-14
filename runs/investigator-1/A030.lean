import ChainOfProof
open ChainOfProof

namespace Cert.A030

def cited : List Fact := [
  ⟨1361, .programRun, 1427230378026551, 1, 908, 909⟩,
  ⟨1358, .programRun, 1427221915797063, 1, 902, 903⟩ ]

def claim : Claim := .both (Sets.programRan 1361) (Sets.programRan 1358)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A030

#print axioms Cert.A030.verified
