import ChainOfProof
open ChainOfProof

namespace Cert.A033

def cited : List Fact := [
  ⟨291, .webSearch, 1427133729303892, 1, 164, 159⟩,
  ⟨470, .tag, 1794614400000000, 1, 164, 229⟩,
  ⟨292, .webSearch, 1427133764343210, 1, 165, 159⟩,
  ⟨483, .tag, 1794614400000000, 1, 165, 229⟩,
  ⟨295, .webSearch, 1427133820424839, 1, 166, 159⟩,
  ⟨480, .tag, 1794614400000000, 1, 166, 229⟩,
  ⟨301, .webSearch, 1427133948655159, 1, 167, 159⟩,
  ⟨481, .tag, 1794614400000000, 1, 167, 229⟩,
  ⟨302, .webSearch, 1427133987545120, 1, 168, 159⟩,
  ⟨478, .tag, 1794614400000000, 1, 168, 229⟩ ]

def claim : Claim := .both (Sets.searched 291) (.both (Sets.tagged 291 .obj 470 229) (.both (Sets.searched 292) (.both (Sets.tagged 292 .obj 483 229) (.both (Sets.searched 295) (.both (Sets.tagged 295 .obj 480 229) (.both (Sets.searched 301) (.both (Sets.tagged 301 .obj 481 229) (.both (Sets.searched 302) (Sets.tagged 302 .obj 478 229)))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A033

#print axioms Cert.A033.verified
