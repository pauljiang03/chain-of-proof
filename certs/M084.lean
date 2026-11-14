import ChainOfProof
open ChainOfProof

namespace Cert.M084

def cited : List Fact := [
  ⟨70, .fileCreated, 1424037140430000, 10000, 18, 19⟩,
  ⟨213, .fileModified, 1419018826000000, 10000, 18, 19⟩,
  ⟨405, .tag, 1794614400000000, 1, 18, 231⟩,
  ⟨406, .tag, 1794614400000000, 1, 18, 235⟩ ]

def claim : Claim := .both (Sets.copiedHere 70 213) (.both (Sets.tagged 70 .obj 405 231) (Sets.tagged 70 .obj 406 235))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M084

#print axioms Cert.M084.verified
