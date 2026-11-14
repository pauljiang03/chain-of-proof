import ChainOfProof
open ChainOfProof

namespace Cert.A078

def cited : List Fact := [
  ⟨12714, .fileContent, 1794614400000000, 1, 93, 16122⟩,
  ⟨12756, .fileContent, 1794614400000000, 1, 113, 16122⟩,
  ⟨12724, .fileContent, 1794614400000000, 1, 103, 16147⟩,
  ⟨12775, .fileContent, 1794614400000000, 1, 132, 16147⟩,
  ⟨12715, .fileContent, 1794614400000000, 1, 94, 16140⟩,
  ⟨12761, .fileContent, 1794614400000000, 1, 115, 16140⟩,
  ⟨12719, .fileContent, 1794614400000000, 1, 98, 16144⟩,
  ⟨12768, .fileContent, 1794614400000000, 1, 123, 16144⟩,
  ⟨12718, .fileContent, 1794614400000000, 1, 97, 16143⟩,
  ⟨12764, .fileContent, 1794614400000000, 1, 121, 16143⟩ ]

def claim : Claim := .both (Sets.sameContent 12714 12756) (.both (Sets.sameContent 12724 12775) (.both (Sets.sameContent 12715 12761) (.both (Sets.sameContent 12719 12768) (Sets.sameContent 12718 12764))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A078

#print axioms Cert.A078.verified
