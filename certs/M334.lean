import ChainOfProof
open ChainOfProof

namespace Cert.M334

def cited : List Fact := [
  ⟨12683, .fileContent, 1794614400000000, 1, 42, 16119⟩,
  ⟨12684, .fileContent, 1794614400000000, 1, 41, 16120⟩,
  ⟨12685, .fileContent, 1794614400000000, 1, 22, 16121⟩,
  ⟨12686, .fileContent, 1794614400000000, 1, 51, 16122⟩,
  ⟨12687, .fileContent, 1794614400000000, 1, 52, 16123⟩,
  ⟨12688, .fileContent, 1794614400000000, 1, 53, 16124⟩,
  ⟨12689, .fileContent, 1794614400000000, 1, 18, 16125⟩,
  ⟨12690, .fileContent, 1794614400000000, 1, 43, 16126⟩,
  ⟨12691, .fileContent, 1794614400000000, 1, 58, 16127⟩,
  ⟨12692, .fileContent, 1794614400000000, 1, 46, 16128⟩,
  ⟨12693, .fileContent, 1794614400000000, 1, 49, 16129⟩,
  ⟨12694, .fileContent, 1794614400000000, 1, 59, 16127⟩,
  ⟨12695, .fileContent, 1794614400000000, 1, 47, 16128⟩,
  ⟨12696, .fileContent, 1794614400000000, 1, 50, 16129⟩,
  ⟨12697, .fileContent, 1794614400000000, 1, 48, 16130⟩,
  ⟨12698, .fileContent, 1794614400000000, 1, 60, 16131⟩,
  ⟨12699, .fileContent, 1794614400000000, 1, 61, 16132⟩,
  ⟨12700, .fileContent, 1794614400000000, 1, 62, 16133⟩,
  ⟨12701, .fileContent, 1794614400000000, 1, 57, 16134⟩,
  ⟨12702, .fileContent, 1794614400000000, 1, 44, 16135⟩,
  ⟨12703, .fileContent, 1794614400000000, 1, 45, 16136⟩,
  ⟨12704, .fileContent, 1794614400000000, 1, 54, 16131⟩,
  ⟨12705, .fileContent, 1794614400000000, 1, 55, 16132⟩,
  ⟨12706, .fileContent, 1794614400000000, 1, 56, 16133⟩,
  ⟨12707, .fileContent, 1794614400000000, 1, 67, 16137⟩,
  ⟨12708, .fileContent, 1794614400000000, 1, 66, 16138⟩,
  ⟨12709, .fileContent, 1794614400000000, 1, 63, 16131⟩,
  ⟨12710, .fileContent, 1794614400000000, 1, 64, 16132⟩,
  ⟨12711, .fileContent, 1794614400000000, 1, 65, 16133⟩,
  ⟨12712, .fileContent, 1794614400000000, 1, 109, 16139⟩,
  ⟨12713, .fileContent, 1794614400000000, 1, 92, 16123⟩,
  ⟨12714, .fileContent, 1794614400000000, 1, 93, 16122⟩,
  ⟨12715, .fileContent, 1794614400000000, 1, 94, 16140⟩,
  ⟨12716, .fileContent, 1794614400000000, 1, 95, 16141⟩,
  ⟨12717, .fileContent, 1794614400000000, 1, 96, 16142⟩,
  ⟨12718, .fileContent, 1794614400000000, 1, 97, 16143⟩,
  ⟨12719, .fileContent, 1794614400000000, 1, 98, 16144⟩,
  ⟨12720, .fileContent, 1794614400000000, 1, 99, 16145⟩,
  ⟨12721, .fileContent, 1794614400000000, 1, 100, 16146⟩,
  ⟨12722, .fileContent, 1794614400000000, 1, 101, 16124⟩ ]

def claim : Claim := .both (Sets.contentHashed 12683) (.both (Sets.contentHashed 12684) (.both (Sets.contentHashed 12685) (.both (Sets.contentHashed 12686) (.both (Sets.contentHashed 12687) (.both (Sets.contentHashed 12688) (.both (Sets.contentHashed 12689) (.both (Sets.contentHashed 12690) (.both (Sets.contentHashed 12691) (.both (Sets.contentHashed 12692) (.both (Sets.contentHashed 12693) (.both (Sets.contentHashed 12694) (.both (Sets.contentHashed 12695) (.both (Sets.contentHashed 12696) (.both (Sets.contentHashed 12697) (.both (Sets.contentHashed 12698) (.both (Sets.contentHashed 12699) (.both (Sets.contentHashed 12700) (.both (Sets.contentHashed 12701) (.both (Sets.contentHashed 12702) (.both (Sets.contentHashed 12703) (.both (Sets.contentHashed 12704) (.both (Sets.contentHashed 12705) (.both (Sets.contentHashed 12706) (.both (Sets.contentHashed 12707) (.both (Sets.contentHashed 12708) (.both (Sets.contentHashed 12709) (.both (Sets.contentHashed 12710) (.both (Sets.contentHashed 12711) (.both (Sets.contentHashed 12712) (.both (Sets.contentHashed 12713) (.both (Sets.contentHashed 12714) (.both (Sets.contentHashed 12715) (.both (Sets.contentHashed 12716) (.both (Sets.contentHashed 12717) (.both (Sets.contentHashed 12718) (.both (Sets.contentHashed 12719) (.both (Sets.contentHashed 12720) (.both (Sets.contentHashed 12721) (Sets.contentHashed 12722)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M334

#print axioms Cert.M334.verified
