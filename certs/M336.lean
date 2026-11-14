import ChainOfProof
open ChainOfProof

namespace Cert.M336

def cited : List Fact := [
  ⟨12763, .fileContent, 1794614400000000, 1, 119, 16142⟩,
  ⟨12764, .fileContent, 1794614400000000, 1, 121, 16143⟩,
  ⟨12765, .fileContent, 1794614400000000, 1, 122, 16144⟩,
  ⟨12766, .fileContent, 1794614400000000, 1, 124, 16145⟩,
  ⟨12767, .fileContent, 1794614400000000, 1, 126, 16146⟩,
  ⟨12768, .fileContent, 1794614400000000, 1, 123, 16144⟩,
  ⟨12769, .fileContent, 1794614400000000, 1, 125, 16145⟩,
  ⟨12770, .fileContent, 1794614400000000, 1, 127, 16146⟩,
  ⟨12771, .fileContent, 1794614400000000, 1, 128, 16124⟩,
  ⟨12772, .fileContent, 1794614400000000, 1, 130, 16125⟩,
  ⟨12773, .fileContent, 1794614400000000, 1, 129, 16124⟩,
  ⟨12774, .fileContent, 1794614400000000, 1, 131, 16125⟩,
  ⟨12775, .fileContent, 1794614400000000, 1, 132, 16147⟩,
  ⟨12776, .fileContent, 1794614400000000, 1, 133, 16148⟩,
  ⟨12777, .fileContent, 1794614400000000, 1, 136, 16149⟩,
  ⟨12778, .fileContent, 1794614400000000, 1, 138, 16150⟩,
  ⟨12779, .fileContent, 1794614400000000, 1, 140, 16151⟩,
  ⟨12780, .fileContent, 1794614400000000, 1, 142, 16152⟩,
  ⟨12781, .fileContent, 1794614400000000, 1, 134, 16147⟩,
  ⟨12782, .fileContent, 1794614400000000, 1, 135, 16148⟩,
  ⟨12783, .fileContent, 1794614400000000, 1, 137, 16149⟩,
  ⟨12784, .fileContent, 1794614400000000, 1, 139, 16150⟩,
  ⟨12785, .fileContent, 1794614400000000, 1, 141, 16151⟩,
  ⟨12786, .fileContent, 1794614400000000, 1, 143, 16152⟩ ]

def claim : Claim := .both (Sets.contentHashed 12763) (.both (Sets.contentHashed 12764) (.both (Sets.contentHashed 12765) (.both (Sets.contentHashed 12766) (.both (Sets.contentHashed 12767) (.both (Sets.contentHashed 12768) (.both (Sets.contentHashed 12769) (.both (Sets.contentHashed 12770) (.both (Sets.contentHashed 12771) (.both (Sets.contentHashed 12772) (.both (Sets.contentHashed 12773) (.both (Sets.contentHashed 12774) (.both (Sets.contentHashed 12775) (.both (Sets.contentHashed 12776) (.both (Sets.contentHashed 12777) (.both (Sets.contentHashed 12778) (.both (Sets.contentHashed 12779) (.both (Sets.contentHashed 12780) (.both (Sets.contentHashed 12781) (.both (Sets.contentHashed 12782) (.both (Sets.contentHashed 12783) (.both (Sets.contentHashed 12784) (.both (Sets.contentHashed 12785) (Sets.contentHashed 12786)))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M336

#print axioms Cert.M336.verified
