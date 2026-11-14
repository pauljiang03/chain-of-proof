import ChainOfProof
open ChainOfProof

namespace Cert.A048

def cited : List Fact := [
  ⟨374, .emailSent, 1427143279000000, 1000000, 213, 206⟩,
  ⟨393, .tag, 1794614400000000, 1, 213, 230⟩,
  ⟨375, .emailSent, 1427203557000000, 1000000, 214, 206⟩,
  ⟨376, .emailSent, 1427204110365000, 1000000, 215, 208⟩,
  ⟨394, .tag, 1794614400000000, 1, 215, 230⟩,
  ⟨377, .emailSent, 1427225642435000, 1000000, 216, 208⟩,
  ⟨395, .tag, 1794614400000000, 1, 216, 230⟩,
  ⟨378, .emailSent, 1427231109679000, 1000000, 217, 208⟩,
  ⟨391, .tag, 1794614400000000, 1, 217, 230⟩ ]

def claim : Claim := .both (Sets.emailed 374) (.both (Sets.tagged 374 .obj 393 230) (.both (Sets.emailed 375) (.both (Sets.emailed 376) (.both (Sets.tagged 376 .obj 394 230) (.both (Sets.emailed 377) (.both (Sets.tagged 377 .obj 395 230) (.both (Sets.emailed 378) (Sets.tagged 378 .obj 391 230))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A048

#print axioms Cert.A048.verified
