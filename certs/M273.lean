import ChainOfProof
open ChainOfProof

namespace Cert.M273

def cited : List Fact := [
  ⟨2115, .webVisit, 1427210596123574, 1, 1344, 881⟩,
  ⟨2116, .webVisit, 1427212899966272, 1, 1345, 881⟩,
  ⟨2117, .webVisit, 1427212899966272, 1, 1345, 881⟩,
  ⟨2118, .webVisit, 1427213801528043, 1, 1346, 881⟩,
  ⟨2119, .webVisit, 1427213801528043, 1, 1346, 881⟩,
  ⟨2120, .webVisit, 1427214703349064, 1, 1347, 881⟩,
  ⟨2121, .webVisit, 1427214703349064, 1, 1347, 881⟩,
  ⟨2122, .webVisit, 1427215604673386, 1, 1348, 881⟩,
  ⟨2123, .webVisit, 1427215604673386, 1, 1348, 881⟩,
  ⟨2124, .webVisit, 1427216505985935, 1, 1349, 881⟩,
  ⟨2125, .webVisit, 1427216505985935, 1, 1349, 881⟩,
  ⟨2126, .webVisit, 1427217407038338, 1, 1350, 881⟩,
  ⟨2127, .webVisit, 1427217407038338, 1, 1350, 881⟩,
  ⟨2128, .webVisit, 1427218623160544, 1, 1351, 881⟩,
  ⟨2129, .webVisit, 1427218623160544, 1, 1351, 881⟩,
  ⟨2130, .webVisit, 1427219526379161, 1, 1352, 881⟩,
  ⟨2131, .webVisit, 1427219526379161, 1, 1352, 881⟩,
  ⟨2132, .webVisit, 1427220429535856, 1, 1353, 881⟩,
  ⟨2133, .webVisit, 1427220429535856, 1, 1353, 881⟩,
  ⟨2134, .webVisit, 1427221332067387, 1, 1354, 881⟩,
  ⟨2135, .webVisit, 1427221332067387, 1, 1354, 881⟩,
  ⟨2136, .webVisit, 1427222627320332, 1, 1355, 881⟩,
  ⟨2137, .webVisit, 1427222627320332, 1, 1355, 881⟩,
  ⟨2138, .webVisit, 1427223592488110, 1, 1356, 881⟩,
  ⟨2139, .webVisit, 1427223592488110, 1, 1356, 881⟩,
  ⟨2140, .webVisit, 1427223604296233, 1, 1357, 881⟩,
  ⟨2141, .webVisit, 1427223604296233, 1, 1357, 881⟩,
  ⟨2142, .webVisit, 1427223627188527, 1, 1358, 881⟩,
  ⟨2143, .webVisit, 1427223627188527, 1, 1358, 881⟩,
  ⟨2144, .webVisit, 1427223653926004, 1, 1359, 881⟩,
  ⟨2145, .webVisit, 1427223653926004, 1, 1359, 881⟩,
  ⟨2146, .webVisit, 1427223657223339, 1, 1360, 881⟩,
  ⟨2147, .webVisit, 1427223657223339, 1, 1360, 881⟩,
  ⟨2148, .webVisit, 1427223670563656, 1, 1361, 881⟩,
  ⟨2149, .webVisit, 1427223670563656, 1, 1361, 881⟩,
  ⟨2150, .webVisit, 1427223677125873, 1, 1115, 881⟩,
  ⟨2151, .webVisit, 1427223677125873, 1, 1115, 881⟩,
  ⟨2152, .webVisit, 1427223678037317, 1, 1361, 881⟩,
  ⟨2153, .webVisit, 1427223678037317, 1, 1361, 881⟩,
  ⟨2154, .webVisit, 1427223680890928, 1, 1114, 881⟩ ]

def claim : Claim := .both (Sets.visited 2115) (.both (Sets.visited 2116) (.both (Sets.visited 2117) (.both (Sets.visited 2118) (.both (Sets.visited 2119) (.both (Sets.visited 2120) (.both (Sets.visited 2121) (.both (Sets.visited 2122) (.both (Sets.visited 2123) (.both (Sets.visited 2124) (.both (Sets.visited 2125) (.both (Sets.visited 2126) (.both (Sets.visited 2127) (.both (Sets.visited 2128) (.both (Sets.visited 2129) (.both (Sets.visited 2130) (.both (Sets.visited 2131) (.both (Sets.visited 2132) (.both (Sets.visited 2133) (.both (Sets.visited 2134) (.both (Sets.visited 2135) (.both (Sets.visited 2136) (.both (Sets.visited 2137) (.both (Sets.visited 2138) (.both (Sets.visited 2139) (.both (Sets.visited 2140) (.both (Sets.visited 2141) (.both (Sets.visited 2142) (.both (Sets.visited 2143) (.both (Sets.visited 2144) (.both (Sets.visited 2145) (.both (Sets.visited 2146) (.both (Sets.visited 2147) (.both (Sets.visited 2148) (.both (Sets.visited 2149) (.both (Sets.visited 2150) (.both (Sets.visited 2151) (.both (Sets.visited 2152) (.both (Sets.visited 2153) (Sets.visited 2154)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M273

#print axioms Cert.M273.verified
