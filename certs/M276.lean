import ChainOfProof
open ChainOfProof

namespace Cert.M276

def cited : List Fact := [
  ⟨2235, .webVisit, 1427294902751205, 1, 1404, 1095⟩,
  ⟨2236, .webVisit, 1427294902753705, 1, 1405, 1095⟩,
  ⟨2237, .webVisit, 1427294902753705, 1, 1401, 1095⟩,
  ⟨2238, .webVisit, 1427294902753705, 1, 1402, 1095⟩,
  ⟨2239, .webVisit, 1427294902756205, 1, 1406, 1095⟩,
  ⟨2240, .webVisit, 1427294902828705, 1, 1407, 1095⟩,
  ⟨2241, .webVisit, 1427294919616205, 1, 1404, 1095⟩,
  ⟨2242, .webVisit, 1427294964856305, 1, 1337, 1095⟩,
  ⟨2243, .webVisit, 1427294964871000, 1, 1337, 1095⟩,
  ⟨2244, .webVisit, 1427294964871905, 1, 1337, 1095⟩,
  ⟨2245, .webVisit, 1427294965700605, 1, 1094, 1095⟩,
  ⟨2246, .webVisit, 1427294965700605, 1, 1337, 1095⟩,
  ⟨2247, .webVisit, 1427295509798005, 1, 1408, 1095⟩,
  ⟨2248, .webVisit, 1427295509798005, 1, 1408, 1095⟩,
  ⟨2249, .webVisit, 1427296928809005, 1, 1409, 1095⟩,
  ⟨2250, .webVisit, 1427296928871405, 1, 1409, 1095⟩,
  ⟨2251, .webVisit, 1427296928887005, 1, 1410, 1095⟩,
  ⟨2252, .webVisit, 1427296928887005, 1, 1410, 1095⟩,
  ⟨2253, .webVisit, 1427296929058605, 1, 1411, 1095⟩,
  ⟨2254, .webVisit, 1427296929230205, 1, 1409, 1095⟩,
  ⟨2255, .webVisit, 1427296929339405, 1, 1412, 1095⟩,
  ⟨2256, .webVisit, 1427297091703000, 1, 1241, 1095⟩,
  ⟨2257, .webVisit, 1427297091703205, 1, 1241, 1095⟩,
  ⟨2258, .webVisit, 1427297313663000, 1, 1413, 1095⟩,
  ⟨2259, .webVisit, 1427297313663205, 1, 1413, 1095⟩,
  ⟨2260, .webVisit, 1427297348981000, 1, 1362, 1095⟩,
  ⟨2261, .webVisit, 1427297348981605, 1, 1362, 1095⟩ ]

def claim : Claim := .both (Sets.visited 2235) (.both (Sets.visited 2236) (.both (Sets.visited 2237) (.both (Sets.visited 2238) (.both (Sets.visited 2239) (.both (Sets.visited 2240) (.both (Sets.visited 2241) (.both (Sets.visited 2242) (.both (Sets.visited 2243) (.both (Sets.visited 2244) (.both (Sets.visited 2245) (.both (Sets.visited 2246) (.both (Sets.visited 2247) (.both (Sets.visited 2248) (.both (Sets.visited 2249) (.both (Sets.visited 2250) (.both (Sets.visited 2251) (.both (Sets.visited 2252) (.both (Sets.visited 2253) (.both (Sets.visited 2254) (.both (Sets.visited 2255) (.both (Sets.visited 2256) (.both (Sets.visited 2257) (.both (Sets.visited 2258) (.both (Sets.visited 2259) (.both (Sets.visited 2260) (Sets.visited 2261))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M276

#print axioms Cert.M276.verified
